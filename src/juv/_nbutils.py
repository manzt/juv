from __future__ import annotations

from typing import TYPE_CHECKING

import jupytext
import nbformat.v4.nbbase as nb

if TYPE_CHECKING:
    from pathlib import Path


def code_cell(source: str, *, hidden: bool = False) -> dict:
    kwargs = {}
    if hidden:
        kwargs["metadata"] = {"jupyter": {"source_hidden": hidden}}

    return nb.new_code_cell(source, **kwargs)


def new_notebook(cells: list[dict]) -> dict:
    notebook = nb.new_notebook(cells=cells)
    if "kernelspec" not in notebook.metadata:
        notebook.metadata.kernelspec = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }
    return notebook


def write_ipynb(nb: dict, file: Path) -> None:
    file.write_text(jupytext.writes(nb, fmt="ipynb"))
