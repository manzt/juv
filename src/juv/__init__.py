"""A wrapper around `uv` to launch ephemeral Jupyter notebooks."""

from __future__ import annotations

import pathlib
import re
import tomllib
import dataclasses
import sys
import shutil
import os
import typing
import tempfile
import subprocess

import rich
import jupytext
from nbformat.v4.nbbase import new_code_cell


@dataclasses.dataclass
class Pep723Meta:
    dependencies: list[str]
    requires_python: str | None


REGEX = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"

Command = typing.Literal["lab", "notebook", "nbclassic", "add"]
COMMANDS = {"lab", "notebook", "nbclassic", "add"}


def parse_pep723_meta(script: str) -> Pep723Meta | None:
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
            parse_pep723_meta("".join(cell["source"]))
            for cell in filter(lambda c: c["cell_type"] == "code", nb.get("cells", []))
        ),
        None,
    )

    return meta, nb


def assert_uv_available():
    if shutil.which("uv") is None:
        print("Error: 'uv' command not found.", file=sys.stderr)
        print("Please install 'uv' to run `juv`.", file=sys.stderr)
        print(
            "For more information, visit: https://github.com/astral-sh/uv",
            file=sys.stderr,
        )
        sys.exit(1)


def build_command(
    nb_path: pathlib.Path,
    pep723_meta: Pep723Meta | None,
    command: Command,
    pre_args: list[str],
    command_version: str | None,
) -> list[str]:
    cmd = ["uvx", "--from=jupyter-core", "--with=setuptools"]

    if pep723_meta:
        # only add --python if not specified by user and present in meta
        if pep723_meta.requires_python and not any(
            x.startswith("--python") for x in pre_args
        ):
            cmd.append(f"--python={pep723_meta.requires_python}")

        cmd.append(f"--with={','.join(pep723_meta.dependencies)}")

    dependency = {
        "lab": "jupyterlab",
        "notebook": "notebook",
        "nbclassic": "nbclassic",
    }[command]

    cmd.append(
        f"--with={dependency}{'==' + command_version if command_version else ''}"
    )
    cmd.extend([*pre_args, "jupyter", command, str(nb_path)])
    return cmd


def run_notebook(
    nb_path: pathlib.Path,
    pep723_meta: Pep723Meta | None,
    command: Command,
    pre_args: list[str],
    command_version: str | None,
) -> None:
    assert_uv_available()
    cmd = build_command(nb_path, pep723_meta, command, pre_args, command_version)
    try:
        os.execvp(cmd[0], cmd)
    except OSError as e:
        print(f"Error executing {cmd[0]}: {e}", file=sys.stderr)
        sys.exit(1)


def split_args() -> tuple[list[str], list[str], str | None]:
    for i, arg in enumerate(sys.argv):
        if arg in COMMANDS:
            return sys.argv[1:i], sys.argv[i:], None

        if (
            arg.startswith("lab@")
            or arg.startswith("notebook@")
            or arg.startswith("nbclassic@")
        ):
            # replace the command with the actual command but get the version
            command, version = sys.argv[i].split("@", 1)
            return sys.argv[1:i], [command] + sys.argv[i + 1 :], version

    return [], sys.argv, None


def update_or_add_inline_meta(nb: dict, deps: list[str]) -> None:
    def includes_inline_meta(cell: dict) -> bool:
        return cell["cell_type"] == "code" and (
            re.search(REGEX, "".join(cell["source"])) is not None
        )

    with tempfile.NamedTemporaryFile(mode="w+", delete=True) as f:
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


def is_command(command: typing.Any) -> typing.TypeGuard[Command]:
    return command in COMMANDS


def write_nb(nb: dict, file: pathlib.Path) -> None:
    file.write_text(jupytext.writes(nb, fmt="ipynb"))


def main() -> None:
    uv_args, args, command_version = split_args()

    help = r"""A wrapper around [cyan]uv[/cyan] to launch ephemeral Jupyter notebooks.

[b]Usage[/b]: juv \[uvx flags] <COMMAND>\[@version] \[PATH]

[b]Commands[/b]:
  [cyan]lab[/cyan]: Launch JupyterLab
  [cyan]notebook[/cyan]: Launch Jupyter Notebook
  [cyan]nbclassic[/cyan]: Launch Jupyter Notebook Classic
  [cyan]add[/cyan]: Add dependencies to the notebook

[b]Examples[/b]:
  uvx juv lab script.py
  uvx juv nbclassic script.py
  uvx juv notebook existing_notebook.ipynb
  uvx juv --python=3.8 notebook@6.4.0 script.ipynb"""

    if "-h" in sys.argv or "--help" in sys.argv:
        rich.print(help)
        sys.exit(0)

    command = args[0] if args else None
    file = args[1] if len(args) > 1 else None

    if not is_command(command) or not file:
        rich.print(help)
        sys.exit(1)

    file = pathlib.Path(file)

    if not file.exists():
        print(f"Error: {file} does not exist.", file=sys.stderr)
        sys.exit(1)

    meta, nb = to_notebook(file)

    if command == "add":
        assert len(args) > 2, "Missing dependencies"
        update_or_add_inline_meta(nb, args[2:])
        write_nb(nb, file.with_suffix(".ipynb"))
        rich.print(f"Updated [cyan]{file.resolve().absolute()}[/cyan]")
        return

    if file.suffix == ".py":
        file = file.with_suffix(".ipynb")
        write_nb(nb, file)

    run_notebook(file, meta, command, uv_args, command_version)


if __name__ == "__main__":
    main()
