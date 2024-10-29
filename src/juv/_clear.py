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
