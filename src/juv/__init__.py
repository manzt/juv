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

import rich
import jupytext
from nbformat.v4.nbbase import new_code_cell, new_notebook

from ._sources import resolve_source, RemoteSource, LocalSource, StdinSource
from ._commands import Command, Version, Init, Add, Info, Lab, Notebook, NbClassic


@dataclasses.dataclass
class Pep723Meta:
    dependencies: list[str]
    requires_python: str | None


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


def load_script_notebook(script: str) -> dict:
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
            nb = load_script_notebook(fp.read_text())
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


def get_juv_temp_dir() -> Path:
    juv_temp_dir = Path(tempfile.gettempdir()) / "juv"
    juv_temp_dir.mkdir(parents=True, exist_ok=True)
    return juv_temp_dir


def parse_args(args: list[str]) -> Command:
    help = r"""A wrapper around [cyan]uv[/cyan] to launch ephemeral Jupyter notebooks.

[b]Usage[/b]: juv \[uvx flags] <COMMAND>\[@version] \[PATH]

[b]Commands[/b]:
  [cyan]init[/cyan]: Initialize a new notebook
  [cyan]add[/cyan]: Add dependencies to the notebook
  [cyan]lab[/cyan]: Launch notebook/script in Jupyter Lab
  [cyan]notebook[/cyan]: Launch notebook/script in Jupyter Notebook
  [cyan]nbclassic[/cyan]: Launch notebook/script in Jupyter Notebook Classic
  [cyan]version[/cyan]: Display juv's version
  [cyan]info[/cyan]: Display juv and uv versions

[b]Examples[/b]:
  juv init foo.ipynb
  juv add foo.ipynb numpy pandas
  juv lab foo.ipynb
  juv nbclassic script.py
  juv --python=3.8 notebook@6.4.0 foo.ipynb"""

    if len(args) == 0:
        rich.print(help)
        sys.exit(1)

    if "-h" in args or "--help" in args or len(args) == 0:
        rich.print(help)
        sys.exit(0)

    if "--version" in args:
        return Version()

    command, *argv = args

    match command:
        case "version":
            return Version()
        case "info":
            return Info()

    source = resolve_source(argv[0]) if len(argv) >= 1 else None

    match (command, source):
        case ("init", None):
            path = pathlib.Path(argv[0]) if len(argv) >= 1 else None
            return Init(path, argv[1:])
        case ("init", LocalSource(file)):
            return Init(file, argv[1:])
        case ("init", RemoteSource(_) | StdinSource()):
            raise ValueError("Remote sources are not supported for init command")
        case ("add", LocalSource(file)):
            return Add(file, argv[1:])
        case ("add", RemoteSource(_) | StdinSource()):
            raise ValueError("Remote sources are not supported for add command")

    match source:
        case LocalSource(file):
            path = file
        case StdinSource():
            with tempfile.NamedTemporaryFile(
                dir=get_juv_temp_dir(), delete=False, suffix=".ipynb", prefix="juv_"
            ) as f:
                path = Path(f.name)
                path.write_text(sys.stdin.read())
        case RemoteSource(href):
            import urllib.request

            temp_file = tempfile.NamedTemporaryFile(
                dir=get_juv_temp_dir(), delete=False, suffix=".ipynb", prefix="juv_"
            )
            path = Path(temp_file.name)
            with urllib.request.urlopen(href) as response:
                content = response.read().decode("utf-8")
                if href.endswith(".py"):
                    nb = load_script_notebook(content)
                    write_nb(nb, path)
                else:
                    path.write_bytes(content)
        case _:
            raise ValueError("Must provide a local or remote source")

    match command.split("@"):
        case ["lab"]:
            return Lab(path)
        case ["lab", version]:
            return Lab(path, version)
        case ["notebook"]:
            return Notebook(path)
        case ["notebook", version]:
            return Notebook(path, version)
        case ["nbclassic"]:
            return NbClassic(path)
        case ["nbclassic", version]:
            return NbClassic(path, version)
        case _:
            rich.print(help)
            sys.exit(1)


def run_version():
    import importlib.metadata

    print(f"juv {importlib.metadata.version('juv')}")


def run_info():
    run_version()
    uv_version = subprocess.run(["uv", "version"], capture_output=True, text=True)
    print(uv_version.stdout)


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
        case Info():
            run_info()
        case Init(file, extra):
            run_init(file, extra)
        case Add(file, packages):
            run_add(file, packages)
        case notebook_command:
            run_notebook(notebook_command, uv_args)
