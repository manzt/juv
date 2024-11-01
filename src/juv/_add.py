from __future__ import annotations

import tempfile
import typing

import jupytext

from ._nbutils import code_cell, write_ipynb
from ._pep723 import includes_inline_metadata
from ._uv import uv

if typing.TYPE_CHECKING:
    from pathlib import Path

T = typing.TypeVar("T")


def find(cb: typing.Callable[[T], bool], items: list[T]) -> T | None:
    """Find the first item in a list that satisfies a condition.

    Parameters
    ----------
    cb : Callable[[T], bool]
        The condition to satisfy.
    items : list[T]
        The list to search.

    Returns
    -------
    T | None
        The first item that satisfies the condition, or None if no item does.

    """
    return next((item for item in items if cb(item)), None)


def add(  # noqa: PLR0913
    path: Path,
    packages: typing.Sequence[str],
    requirements: str | None = None,
    extras: typing.Sequence[str] | None = None,
    tag: str | None = None,
    branch: str | None = None,
    rev: str | None = None,
    *,
    editable: bool = False,
) -> None:
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
        encoding="utf-8",
    ) as f:
        f.write(cell["source"].strip())
        f.flush()

        uv(
            [
                "add",
                *(["--requirements", requirements] if requirements else []),
                *([f"--extra={extra}" for extra in extras or []]),
                *(["--editable"] if editable else []),
                *([f"--tag={tag}"] if tag else []),
                *([f"--branch={branch}"] if branch else []),
                *([f"--rev={rev}"] if rev else []),
                "--script",
                f.name,
                *packages,
            ],
            check=True,
        )

        f.seek(0)
        cell["source"] = f.read().strip()

    write_ipynb(notebook, path.with_suffix(".ipynb"))
