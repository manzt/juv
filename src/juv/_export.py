import sys
import tempfile
from pathlib import Path

import jupytext

from ._nbutils import code_cell, write_ipynb
from ._pep723 import includes_inline_metadata
from ._utils import find
from ._uv import uv


def export(
    path: Path,
    *,
    frozen: bool = False,
) -> None:
    contents = export_to_string(path, frozen=frozen)
    sys.stdout.write(contents)


def export_to_string(
    path: Path,
    *,
    frozen: bool = False,
) -> str:
    notebook = jupytext.read(path, fmt="ipynb")
    lockfile_contents = notebook.get("metadata", {}).get("uv.lock")

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
        lockfile = Path(f"{f.name}.lock")

        f.write(cell["source"].strip())
        f.flush()

        if lockfile_contents:
            lockfile.write_text(lockfile_contents)

        result = uv(["export", "--script", f.name], check=True)
        contents = result.stdout.decode("utf-8")

        if not frozen and lockfile.exists():
            notebook.metadata["uv.lock"] = lockfile.read_text(encoding="utf-8")
            write_ipynb(notebook, path)
            lockfile.unlink(missing_ok=True)

    return contents
