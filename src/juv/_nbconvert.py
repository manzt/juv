from pathlib import Path
import jupytext

import nbformat.v4.nbbase as nb


def code_cell(source: str, hidden: bool = False) -> dict:
    return nb.new_code_cell(
        source,
        metadata={"jupyter": {"source_hidden": hidden}},
    )


def new_notebook(cells: list[dict]) -> dict:
    return nb.new_notebook(cells=cells)


def write_ipynb(nb: dict, file: Path) -> None:
    file.write_text(jupytext.writes(nb, fmt="ipynb"))
