import tempfile
import typing
from pathlib import Path

import jupytext

from ._nbutils import code_cell, write_ipynb
from ._pep723 import includes_inline_metadata
from ._utils import find
from ._uv import uv


def remove(
    path: Path,
    *,
    packages: typing.Sequence[str],
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
                "remove",
                "--script",
                str(f.name),
                *packages,
            ],
            check=True,
        )
        f.seek(0)
        cell["source"] = f.read().strip()

    write_ipynb(notebook, path.with_suffix(".ipynb"))
