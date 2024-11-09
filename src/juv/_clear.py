from __future__ import annotations

from typing import TYPE_CHECKING

import nbformat

if TYPE_CHECKING:
    from pathlib import Path


def clear(path: Path) -> None:
    nb = nbformat.read(path, nbformat.NO_CONVERT)
    # clear cells
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    # clear widgets metadata
    nb.metadata.pop("widgets", None)
    nbformat.write(nb, path)


def is_cleared(path: Path) -> bool:
    """Check if a notebook has been cleared.

    A notebook is considered cleared if:
        - It does not have any outputs or execution counts in code cells.
        - It does not have any widgets metadata.

    Parameters
    ----------
    path : Path
        Path to the notebook file.

    Returns
    -------
    bool
        True if the notebook is cleared, False otherwise

    """
    nb = nbformat.read(path, nbformat.NO_CONVERT)
    if "widgets" in nb.metadata:
        return False
    for cell in filter(lambda cell: cell.cell_type == "code", nb.cells):
        if cell.outputs or cell.execution_count is not None:
            return False
    return True
