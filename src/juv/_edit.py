import subprocess
import tempfile
from pathlib import Path

import jupytext

from ._cat import notebook_contents


class EditorAbortedError(Exception):
    """Exception raised when the editor exits abnormally."""


def open_editor(contents: str, suffix: str, editor: str) -> str:
    """Open an editor with the given contents and return the modified text.

    Args:
        contents: Initial text content
        suffix: File extension for temporary file
        editor: Editor command to use

    Returns:
        str: Modified text content

    Raises:
        EditorAbortedError: If editor exits abnormally

    """
    with tempfile.NamedTemporaryFile(
        suffix=suffix, mode="w+", delete=False, encoding="utf-8"
    ) as tf:
        if contents:
            tf.write(contents)
            tf.flush()
        tpath = Path(tf.name)
    try:
        if any(code in editor.lower() for code in ["code", "vscode"]):
            cmd = [editor, "--wait", tpath]
        else:
            cmd = [editor, tpath]

        result = subprocess.run(cmd, check=False)  # noqa: S603
        if result.returncode != 0:
            msg = f"Editor exited with code {result.returncode}"
            raise EditorAbortedError(msg)
        return tpath.read_text(encoding="utf-8")
    finally:
        tpath.unlink()


def edit(path: Path, editor: str) -> None:
    """Edit a Jupyter notebook as markdown.

    Args:
        path: Path to notebook file
        editor: Editor command to use

    """
    prev_notebook = jupytext.read(path, fmt="ipynb")

    # Create a mapping of cell IDs to previous cells
    prev_cells: dict[str, dict] = {}
    for update in prev_notebook["cells"]:
        if "id" not in update:
            continue
        update["metadata"]["id"] = update["id"]
        prev_cells[update["id"]] = update

    code = notebook_contents(path, script=False)
    text = open_editor(code, suffix=".md", editor=editor)
    new_notebook = jupytext.reads(text.strip(), fmt="md")

    # Update the previous notebook cells with the new ones
    cells = []
    for update in new_notebook["cells"]:
        prev = prev_cells.get(update["metadata"].pop("id", None))
        update["metadata"].pop("lines_to_next_cell", None)
        if prev is None:
            cells.append(update)
            continue
        prev.update(
            {
                "cell_type": update["cell_type"],
                "source": update["source"],
                "metadata": update["metadata"],
            }
        )
        cells.append(prev)

    prev_notebook["cells"] = cells
    path.write_text(jupytext.writes(prev_notebook, fmt="ipynb"))
