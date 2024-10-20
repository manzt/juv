"""A wrapper around `uv` to launch ephemeral Jupyter notebooks."""

from __future__ import annotations

import pathlib
import re
import tomllib
import json
import dataclasses
import sys
import shutil
import os
import typing

import rich
import jupytext


@dataclasses.dataclass
class Pep723Meta:
    dependencies: list[str]
    requires_python: str | None


REGEX = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"

Command = typing.Literal["lab", "notebook", "nbclassic"]


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


def to_notebook(fp: pathlib.Path) -> tuple[Pep723Meta | None, dict]:
    match fp.suffix:
        case ".py":
            nb = jupytext.read(fp)
        case ".ipynb":
            with fp.open() as f:
                nb = json.load(f)
        case _:
            raise ValueError(f"Unsupported file extension: {fp.suffix}")

    cells = nb.get("cells", [])
    meta = next(
        (
            parse_pep723_meta(cell["source"])
            for cell in filter(lambda c: c["cell_type"] == "code", cells)
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
    cmd = ["uvx", "--from", "jupyter-core", "--with", "setuptools"]

    if pep723_meta:
        if pep723_meta.requires_python and not any(
            x.startswith("--python") for x in pre_args
        ):
            cmd.extend(["--python", pep723_meta.requires_python])

        for dep in pep723_meta.dependencies:
            cmd.extend(["--with", dep])

    dep = {
        "lab": "jupyterlab",
        "notebook": "notebook",
        "nbclassic": "nbclassic",
    }[command]

    cmd.extend([
        "--with",
        f"{dep}=={command_version}" if command_version else dep,
    ])

    cmd.extend(pre_args)

    cmd.extend(["jupyter", command, str(nb_path)])
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
        if arg in ["lab", "notebook", "nbclassic"]:
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


def is_command(command: typing.Any) -> typing.TypeGuard[Command]:
    return command in ["lab", "notebook", "nbclassic"]


def main() -> None:
    uv_args, args, command_version = split_args()

    help = r"""A wrapper around [cyan]uv[/cyan] to launch ephemeral Jupyter notebooks.

[b]Usage[/b]: juv \[uvx flags] <COMMAND>\[@version] \[PATH]

[b]Commands[/b]:
  [cyan]lab[/cyan]: Launch JupyterLab
  [cyan]notebook[/cyan]: Launch Jupyter Notebook
  [cyan]nbclassic[/cyan]: Launch Jupyter Notebook Classic

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

    meta, content = to_notebook(file)

    if file.suffix == ".py":
        file = file.with_suffix(".ipynb")
        file.write_text(json.dumps(content, indent=2))

    run_notebook(file, meta, command, uv_args, command_version)


if __name__ == "__main__":
    main()
