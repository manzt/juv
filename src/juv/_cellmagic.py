"""IPython magics for juv sessions.

Note: these utilities are bootstrapped in to the juv session (DO NOT IMPORT).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import typing
from functools import wraps
from pathlib import Path

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class

from ._pep723 import includes_inline_metadata, parse_inline_script_metadata

if typing.TYPE_CHECKING:
    from IPython.core.interactiveshell import InteractiveShell


ENV = {
    "notebook_target": os.environ["JUV_INTERNAL__NOTEBOOK_TARGET"],
    "notebook_extras": os.environ["JUV_INTERNAL__NOTEBOOK_EXTRAS"],
    "uv": os.environ["JUV_INTERNAL__UV"],
}


def get_venv() -> str:
    # Otherwise, check if we're in a venv
    venv_marker = Path(sys.prefix) / "pyvenv.cfg"

    if venv_marker.exists():
        return str(venv_marker.parent)

    msg = "No virtual environment found."
    raise ValueError(msg)


def get_current_meta_comment() -> str | None:
    notebook_path = ENV["notebook_target"]

    with open(notebook_path, encoding="utf-8") as f:  # noqa: PTH123
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
    packages = ENV["notebook_extras"].split(",")

    if meta_str is not None:
        meta_str = parse_inline_script_metadata(meta_str)

        if meta_str:
            meta = tomllib.loads(meta_str)
            packages.extend(meta.get("dependencies", []))

    # Tried just chaining pipes, but it didn't work..
    with tempfile.TemporaryDirectory() as tempdir:
        requirements_txt = Path(tempdir) / "requirements.txt"
        subprocess.run(  # noqa: S603
            [
                ENV["uv"],
                "pip",
                "compile",
                f"--output-file={requirements_txt}",
                "-",
            ],
            input="\n".join(packages).encode("utf-8"),
            capture_output=True,
            check=True,
            env=env,
        )
        subprocess.run(  # noqa: S603
            [
                ENV["uv"],
                "pip",
                "sync",
                str(requirements_txt),
            ],
            capture_output=True,
            check=False,
            env=env,
        )


def is_command(cmd: str) -> typing.TypeGuard[typing.Literal["add", "sync"]]:
    return cmd in {"add", "sync"}


def parse_line(line: str) -> tuple[typing.Literal["add", "sync"], list[str]]:
    args = line.split(" ")
    if not args:
        msg = "No command provided."
        raise ValueError(msg)

    cmd, *args = args
    if not is_command(cmd):
        msg = f"Invalid command: {cmd}"
        raise ValueError(msg)

    return cmd, args


def debounce(
    wait: float,
) -> typing.Callable[[typing.Callable[..., None]], typing.Callable[..., None]]:
    def deco(fn: typing.Callable) -> typing.Callable:
        last_call = 0.0

        @wraps(fn)
        def debounced() -> None:
            nonlocal last_call
            current_time = time.time()
            if current_time - last_call < wait:
                return None
            last_call = current_time
            return fn()

        return debounced

    return deco


@magics_class
class JuvMagics(Magics):
    """A set of IPython magics for working with virtual files."""

    @line_magic("juv")
    @cell_magic("juv")
    def execute(self, line: str = "", cell: str = "") -> None:  # noqa: ARG002
        """Run a juv command."""
        cmd, args = parse_line(line)


LOADED = False


def load_ipython_extension(ipython: InteractiveShell) -> None:
    """Load the IPython extension.

    Parameters
    ----------
    ipython : IPython.core.interactiveshell.InteractiveShell
        The IPython shell instance.

    """
    global LOADED  # noqa: PLW0603
    if LOADED:
        return
    LOADED = True

    inline_meta_comment = get_current_meta_comment()

    # debounce to avoid multiple syncs if cells are run in quick succession
    # (e.g. with shift+enter)
    @debounce(0.5)
    def sync_env() -> None:
        nonlocal inline_meta_comment
        current = get_current_meta_comment()

        if current == inline_meta_comment:
            return

        inline_meta_comment = current
        uv_sync(current)

    ipython.events.register("pre_run_cell", lambda _: sync_env())
    ipython.register_magics(JuvMagics)
