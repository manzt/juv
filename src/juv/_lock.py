import tempfile
from pathlib import Path

import jupytext

from ._nbutils import code_cell, write_ipynb
from ._pep723 import includes_inline_metadata
from ._utils import find
from ._uv import uv


def lock(*, path: Path, clear: bool) -> None:
    notebook = jupytext.read(path, fmt="ipynb")

    if clear:
        notebook.get("metadata", {}).pop("uv.lock", None)
        write_ipynb(notebook, path)
        return

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
    ) as temp_file:
        temp_file.write(cell["source"].strip())
        temp_file.flush()

        uv(["lock", "--script", temp_file.name], check=True)

        lock_file = Path(f"{temp_file.name}.lock")

        notebook["metadata"]["uv.lock"] = lock_file.read_text(encoding="utf-8")

        lock_file.unlink(missing_ok=True)

    write_ipynb(notebook, path.with_suffix(".ipynb"))
