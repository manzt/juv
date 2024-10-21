"""A wrapper around `uv` to launch ephemeral Jupyter notebooks."""

from __future__ import annotations

import pathlib
import re
import tomllib
import dataclasses
import sys
import shutil
import os
import tempfile
import subprocess
from pathlib import Path
import typing

import rich
import jupytext
from nbformat.v4.nbbase import new_code_cell, new_notebook


@dataclasses.dataclass
class Pep723Meta:
    dependencies: list[str]
    requires_python: str | None


@dataclasses.dataclass
class Init:
    file: Path | None = None
    extra: list[str] = dataclasses.field(default_factory=list)
    kind: typing.ClassVar[typing.Literal["init"]] = "init"


@dataclasses.dataclass
class Add:
    file: Path
    packages: list[str]
    kind: typing.ClassVar[typing.Literal["add"]] = "add"


@dataclasses.dataclass
class Lab:
    file: Path
    version: str | None = None
    kind: typing.ClassVar[typing.Literal["lab"]] = "lab"


@dataclasses.dataclass
class Notebook:
    file: Path
    version: str | None = None
    kind: typing.ClassVar[typing.Literal["notebook"]] = "notebook"


@dataclasses.dataclass
class NbClassic:
    file: Path
    version: str | None = None
    kind: typing.ClassVar[typing.Literal["nbclassic"]] = "nbclassic"


@dataclasses.dataclass
class Version: ...


Command = Init | Add | Lab | Notebook | NbClassic | Version


REGEX = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"


def parse_inline_script_metadata(script: str) -> Pep723Meta | None:
    name = "script"
    matches = list(
        filter(lambda m: m.group("type") == name, re.finditer(REGEX, script))
    )
    if len(matches) > 1:
        raise ValueError(f"Multiple {name} blocks found")
    elif len(matches) == 1:
        content = "".join(
            line[2:] if line.startswith("# ") else line[1:]
            for line in matches[0].group("content").splitlines(keepends=True)
        )
        meta = tomllib.loads(content)
        return Pep723Meta(
            dependencies=meta.get("dependencies", []),
            requires_python=meta.get("requires-python"),
        )
    else:
        return None


def nbcell(source: str, hidden: bool = False) -> dict:
    return new_code_cell(
        source,
        metadata={"jupyter": {"source_hidden": hidden}},
    )


def load_script_notebook(fp: pathlib.Path) -> dict:
    script = fp.read_text()
    inline_meta = None
    if meta_block := re.search(REGEX, script):
        inline_meta = meta_block.group(0)
        script = script.replace(inline_meta, "")
    nb = jupytext.reads(script.strip())
    if inline_meta:
        nb["cells"].insert(
            0,
            nbcell(inline_meta.strip(), hidden=True),
        )
    return nb


def to_notebook(fp: pathlib.Path) -> tuple[Pep723Meta | None, dict]:
    match fp.suffix:
        case ".py":
            nb = load_script_notebook(fp)
        case ".ipynb":
            nb = jupytext.read(fp, fmt="ipynb")
        case _:
            raise ValueError(f"Unsupported file extension: {fp.suffix}")

    meta = next(
        (
            parse_inline_script_metadata("".join(cell["source"]))
            for cell in filter(lambda c: c["cell_type"] == "code", nb.get("cells", []))
        ),
        None,
    )

    return meta, nb


def assert_uv_available():
    if shutil.which("uv") is None:
        rich.print("Error: 'uv' command not found.", file=sys.stderr)
        rich.print("Please install 'uv' to run `juv`.", file=sys.stderr)
        rich.print(
            "For more information, visit: https://github.com/astral-sh/uv",
            file=sys.stderr,
        )
        sys.exit(1)


def create_uv_run_command(
    command: Lab | Notebook | NbClassic,
    pep723_meta: Pep723Meta | None,
    pre_args: list[str],
) -> list[str]:
    cmd = ["uvx", "--from=jupyter-core", "--with=setuptools"]

    if pep723_meta:
        # only add --python if not specified by user and present in meta
        if pep723_meta.requires_python and not any(
            x.startswith("--python") for x in pre_args
        ):
            cmd.append(f"--python={pep723_meta.requires_python}")

        if len(pep723_meta.dependencies) > 0:
            cmd.append(f"--with={','.join(pep723_meta.dependencies)}")

    match command:
        case Lab(_, version):
            cmd.append(f"--with=jupyterlab{'==' + version if version else ''}")
        case Notebook(_, version):
            cmd.append(f"--with=notebook{'==' + version if version else ''}")
        case NbClassic(_, version):
            cmd.append(f"--with=nbclassic{'==' + version if version else ''}")

    cmd.extend([*pre_args, "jupyter", command.kind, str(command.file)])
    return cmd


def update_or_add_inline_meta(
    nb: dict,
    deps: list[str],
    dir: pathlib.Path,
) -> None:
    def includes_inline_meta(cell: dict) -> bool:
        return cell["cell_type"] == "code" and (
            re.search(REGEX, "".join(cell["source"])) is not None
        )

    with tempfile.NamedTemporaryFile(
        mode="w+",
        delete=True,
        suffix=".py",
        dir=dir,
    ) as f:
        cell = next(
            (cell for cell in nb["cells"] if includes_inline_meta(cell)),
            None,
        )
        if cell is None:
            nb["cells"].insert(0, nbcell("", hidden=True))
            cell = nb["cells"][0]

        f.write(cell["source"])
        f.flush()
        subprocess.run(["uv", "add", "--quiet", "--script", f.name, *deps])
        f.seek(0)
        cell["source"] = f.read()


def init_notebook(uv_args: list[str], dir: pathlib.Path) -> dict:
    with tempfile.NamedTemporaryFile(
        mode="w+",
        suffix=".py",
        delete=True,
        dir=dir,
    ) as f:
        subprocess.run(["uv", "init", "--quiet", "--script", f.name, *uv_args])
        f.seek(0)
        nb = new_notebook(cells=[nbcell(f.read(), hidden=True)])
    return nb


def write_nb(nb: dict, file: pathlib.Path) -> None:
    file.write_text(jupytext.writes(nb, fmt="ipynb"))


def get_untitled() -> pathlib.Path:
    if not pathlib.Path("Untitled.ipynb").exists():
        return pathlib.Path("Untitled.ipynb")

    for i in range(1, 100):
        file = pathlib.Path(f"Untitled{i}.ipynb")
        if not file.exists():
            return file

    raise ValueError("Could not find an available UntitledX.ipynb")


def parse_args(args: list[str]) -> Command:
    help = r"""A wrapper around [cyan]uv[/cyan] to launch ephemeral Jupyter notebooks.

[b]Usage[/b]: juv \[uvx flags] <COMMAND>\[@version] \[PATH]

[b]Commands[/b]:
  [cyan]init[/cyan]: Initialize a new notebook
  [cyan]add[/cyan]: Add dependencies to the notebook
  [cyan]lab[/cyan]: Launch notebook/script in Jupyter Lab
  [cyan]notebook[/cyan]: Launch notebook/script in Jupyter Notebook
  [cyan]nbclassic[/cyan]: Launch notebook/script in Jupyter Notebook Classic
  [cyan]version[/cyan]: Print version

[b]Examples[/b]:
  juv init foo.ipynb
  juv add foo.ipynb numpy pandas
  juv lab foo.ipynb
  juv nbclassic script.py
  juv --python=3.8 notebook@6.4.0 foo.ipynb"""

    if "-h" in args or "--help" in args or len(args) == 0:
        rich.print(help)
        sys.exit(0)

    command, *argv = args

    match command.split("@"):
        case ["init"]:
            return Init(file=Path(argv[0]) if argv else None, extra=argv[1:])
        case ["add"]:
            return Add(file=Path(argv[0]), packages=argv[1:])
        case ["version"]:
            return Version()
        case ["lab"]:
            return Lab(file=Path(argv[0]))
        case ["lab", version]:
            return Lab(file=Path(argv[0]), version=version)
        case ["notebook"]:
            return Notebook(file=Path(argv[0]))
        case ["notebook", version]:
            return Notebook(file=Path(argv[0]), version=version)
        case ["nbclassic"]:
            return NbClassic(file=Path(argv[0]))
        case ["nbclassic", version]:
            return NbClassic(file=Path(argv[0]), version=version)
        case _:
            rich.print(help)
            sys.exit(1)


def run_init(file: Path | None, extra: list[str]):
    if not file:
        file = get_untitled()
    if not file.suffix == ".ipynb":
        rich.print("File must have a `[cyan].ipynb[/cyan]` extension.", file=sys.stderr)
        sys.exit(1)
    nb = init_notebook(extra, file.parent)
    write_nb(nb, file)
    rich.print(f"Initialized notebook at `[cyan]{file.resolve().absolute()}[/cyan]")


def run_add(file: Path, packages: list[str]):
    if not file.exists():
        rich.print(
            f"Error: `[cyan]{file.resolve().absolute()}[/cyan]` does not exist.",
            file=sys.stderr,
        )
        sys.exit(1)
    _, nb = to_notebook(file)
    update_or_add_inline_meta(nb, packages, file.parent)
    write_nb(nb, file.with_suffix(".ipynb"))
    rich.print(f"Updated `[cyan]{file.resolve().absolute()}[/cyan]`")


def run_notebook(command: Lab | Notebook | NbClassic, uv_args: list[str]):
    if not command.file.exists():
        rich.print(
            f"Error: `[cyan]{command.file.resolve().absolute()}[/cyan]` does not exist.",
            file=sys.stderr,
        )
        sys.exit(1)
    meta, nb = to_notebook(command.file)

    if command.file.suffix == ".py":
        command.file = command.file.with_suffix(".ipynb")
        write_nb(nb, command.file)
        rich.print(
            f"Converted script to notebook `[cyan]{command.file.resolve().absolute()}[/cyan]`"
        )

    cmd = create_uv_run_command(command, meta, uv_args)
    try:
        os.execvp(cmd[0], cmd)
    except OSError as e:
        print(f"Error executing {cmd[0]}: {e}", file=sys.stderr)
        sys.exit(1)


def run_version():
    import importlib.metadata

    print(f"juv {importlib.metadata.version('juv')}")


def split_args(argv: list[str]) -> tuple[list[str], list[str]]:
    kinds = [Lab.kind, Notebook.kind, NbClassic.kind, Init.kind, Add.kind]
    for i, arg in enumerate(argv[1:], start=1):
        if any(arg.startswith(kind) for kind in kinds):
            return argv[1:i], argv[i:]
    return [], argv[1:]


def main():
    uv_args, args = split_args(sys.argv)
    assert_uv_available()
    match parse_args(args):
        case Version():
            run_version()
        case Init(file, extra):
            run_init(file, extra)
        case Add(file, packages):
            run_add(file, packages)
        case notebook_command:
            run_notebook(notebook_command, uv_args)
