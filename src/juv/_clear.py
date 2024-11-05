from __future__ import annotations

from typing import TYPE_CHECKING

import nbformat

if TYPE_CHECKING:
    from pathlib import Path


def clear(path: Path) -> None:
    nb = nbformat.read(path, nbformat.NO_CONVERT)
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    nbformat.write(nb, path)


def is_cleared(path: Path) -> bool:
    """Check if a notebook has been cleared."""
    nb = nbformat.read(path, nbformat.NO_CONVERT)
    for cell in filter(lambda cell: cell.cell_type == "code", nb.cells):
        if cell.outputs or cell.execution_count is not None:
            return False
    return True
