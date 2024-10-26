"""IPython magics for juv sessions.

Note: these utilities are bootstrapped in to the juv session (DO NOT IMPORT).
"""

from __future__ import annotations

import json
import os
import sys
import typing
from pathlib import Path

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class

from ._pep723 import includes_inline_metadata, parse_inline_script_metadata
from ._uv import uv

CMDS = {"add", "sync"}


def get_venv() -> str:
    # If it's already set, then just use it
    value = os.getenv("VIRTUAL_ENV")
    if value:
        return value

    # Otherwise, check if we're in a venv
    venv_marker = Path(sys.prefix) / "pyvenv.cfg"

    if venv_marker.exists():
        return str(venv_marker.parent)

    msg = "No virtual environment found."
    raise ValueError(msg)


def get_current_notebook_path() -> Path:
    notebook = os.environ.get("JUV_CLIENT_NOTEBOOK")
    if notebook is None:
        msg = "No notebook found in environment."
        raise ValueError(msg)
    return Path(notebook)


def get_current_meta_comment() -> str | None:
    notebook_path = get_current_notebook_path()

    with Path.open(notebook_path, "r") as f:
        notebook = json.load(f)

        for cell in notebook["cells"]:
            if cell["cell_type"] != "code":
                continue

            source = "".join(cell["source"])
            if includes_inline_metadata(source):
                return source
    return None


def uv_sync(meta_str: str | None) -> None:
    import tempfile

    import tomllib

    env = os.environ.copy()
    env["VIRTUAL_ENV"] = get_venv()

    packages = os.environ["JUV_CLIENT_PIP_EXTRAS"].split(",")

    if meta_str is not None:
        meta_str = parse_inline_script_metadata(meta_str)

        if meta_str:
            meta = tomllib.loads(meta_str)
            packages.extend(meta.get("dependencies", []))

    with tempfile.TemporaryDirectory() as td:
        requirements_txt = Path(td) / "requirements.txt"
        requirements_txt.write_text("\n".join(packages))
        output = uv(["pip", "sync", str(requirements_txt)], check=True, env=env)
        print(output.stdout.decode())


def parse_line(line: str) -> tuple[typing.Literal["add", "sync"], list[str]]:
    args = line.split(" ")
    if not args:
        msg = "No command provided."
        raise ValueError(msg)

    cmd, *args = args
    if cmd not in CMDS:
        msg = f"Invalid command: {cmd}"
        raise ValueError(msg)

    return cmd, args


@magics_class
class JuvMagics(Magics):
    """A set of IPython magics for working with virtual files."""

    @line_magic("juv")
    @cell_magic("juv")
    def execute(self, line: str = "", cell: str = "") -> None:
        """Run a juv command."""
        cmd, args = parse_line(line)
        notebook = get_current_notebook_path()

        if cmd != "add":
            return


def load_ipython_extension(ipython: InteractiveShell) -> None:
    """Load the IPython extension.

    Parameters
    ----------
    ipython : IPython.core.interactiveshell.InteractiveShell
        The IPython shell instance.

    """
    inline_meta_comment = None

    def sync_env() -> None:
        nonlocal inline_meta_comment
        current = get_current_meta_comment()
        if current == inline_meta_comment:
            return
        uv_sync(current)

    def pre_run_cell(info: dict):
        sync_env()

    ipython.events.register("pre_run_cell", pre_run_cell)
    ipython.register_magics(JuvMagics)
