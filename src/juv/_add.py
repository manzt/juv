from __future__ import annotations
import typing

from pathlib import Path
import tempfile

import jupytext

from ._pep723 import includes_inline_metadata
from ._nbconvert import code_cell, write_ipynb
from ._uv import uv

T = typing.TypeVar("T")


def find(cb: typing.Callable[[T], bool], items: list[T]) -> T | None:
    """Find the first item in a list that satisfies a condition."""
    return next((item for item in items if cb(item)), None)


def add(path: Path, packages: typing.Sequence[str], requirements: str | None) -> None:
    notebook = jupytext.read(path, fmt="ipynb")

    # need a reference so we can modify the cell["source"]
    cell = find(
        lambda cell: (
            cell["cell_type"] == "code"
            and includes_inline_metadata("".join(cell["source"]))
        ),
        notebook["cells"],
    )

    if cell is None:
        notebook["cells"].insert(0, code_cell("", hidden=True))
        cell = notebook["cells"][0]

    with tempfile.NamedTemporaryFile(
        mode="w+",
        delete=True,
        suffix=".py",
        dir=path.parent,
    ) as f:
        f.write(cell["source"].strip())
        f.flush()

        uv(
            [
                "add",
                *(["--requirements", requirements] if requirements else []),
                "--script",
                f.name,
                *packages,
            ],
            check=True,
        )

        f.seek(0)
        cell["source"] = f.read().strip()

    write_ipynb(notebook, path.with_suffix(".ipynb"))
