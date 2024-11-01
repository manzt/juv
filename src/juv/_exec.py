from __future__ import annotations

import os
import subprocess
import sys
import typing

import jupytext
from uv import find_uv_bin

if typing.TYPE_CHECKING:
    from pathlib import Path


def exec_(
    path: Path,
    python: str | None,
    with_args: typing.Sequence[str],
    *,
    quiet: bool,
) -> None:
    target = path.resolve()
    notebook = jupytext.read(target)

    # change to the target's directory
    os.chdir(target.parent)

    subprocess.run(  # noqa: S603
        [
            os.fsdecode(find_uv_bin()),
            "run",
            *([f"--python={python}"] if python else []),
            *(["--with=" + ",".join(with_args)] if with_args else []),
            *(["--quiet"] if quiet else []),
            "-",
        ],
        input=jupytext.writes(notebook, fmt="py").encode(),
        check=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
