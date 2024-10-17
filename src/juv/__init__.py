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


@dataclasses.dataclass
class Pep723Meta:
    dependencies: list[str]
    python_version: str | None


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
            python_version=meta.get("requires-python"),
        )
    else:
        return None


def nbcell(source: str, hidden: bool = False) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"jupyter": {"source_hidden": hidden}},
        "outputs": [],
        "source": source,
    }


def script_to_nb(script: str) -> str:
    """Embeds the a given script as the first cell in a Jupyter notebook."""
    cells: list[dict] = []

    meta_block = re.search(REGEX, script)

    if meta_block:
        meta_block = meta_block.group(0)
        cells.append(nbcell(meta_block, hidden=True))
        script = script.replace(meta_block, "")

    cells.append(nbcell(script.strip()))

    return json.dumps(
        obj={
            "cells": cells,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                }
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        },
        indent=2,
    )


def to_notebook(fp: pathlib.Path) -> tuple[Pep723Meta | None, str]:
    match fp.suffix:
        case ".py":
            content = fp.read_text()
            meta = parse_pep723_meta(content)
            return meta, script_to_nb(content)
        case ".ipynb":
            content = fp.read_text()
            for cell in json.loads(content).get("cells", []):
                if cell.get("cell_type") == "code":
                    meta = parse_pep723_meta(cell["source"])
                    return meta, content

            return None, content
        case _:
            raise ValueError(f"Unsupported file extension: {fp.suffix}")


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
        if pep723_meta.python_version and not any(
            x.startswith("--python") for x in pre_args
        ):
            cmd.extend(["--python", pep723_meta.python_version])

        for dep in pep723_meta.dependencies:
            cmd.extend(["--with", dep])

    if command == "lab":
        cmd.extend(
            [
                "--with",
                f"jupyterlab=={command_version}" if command_version else "jupyterlab",
            ]
        )
    elif command == "notebook":
        cmd.extend(
            [
                "--with",
                f"notebook=={command_version}" if command_version else "notebook",
            ]
        )
    elif command == "nbclassic":
        cmd.extend(
            [
                "--with",
                f"nbclassic=={command_version}" if command_version else "nbclassic",
            ]
        )

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
        file.write_text(content)

    run_notebook(file, meta, command, uv_args, command_version)


if __name__ == "__main__":
    main()
