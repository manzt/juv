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
    return nb.new_notebook(cells=cells)


def write_ipynb(nb: dict, file: Path) -> None:
    file.write_text(jupytext.writes(nb, fmt="ipynb"))
