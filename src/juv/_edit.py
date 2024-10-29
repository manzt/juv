import subprocess
import tempfile
from pathlib import Path

import jupytext

from ._cat import cat
from ._pep723 import includes_inline_metadata


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

    text = open_editor(cat(prev_notebook, fmt="md"), suffix=".md", editor=editor)
    new_notebook = jupytext.reads(text.strip(), fmt="md")

    # Preserves thing like the outputs and execution count, probably should just
    # override but you can use `juv clean` for that.
    for old_cell, new_cell in zip(prev_notebook["cells"], new_notebook["cells"]):
        old_cell["cell_type"] = new_cell["cell_type"]
        old_cell["source"] = new_cell["source"]
        old_cell["metadata"] = new_cell["metadata"]

    path.write_text(jupytext.writes(prev_notebook, fmt="ipynb"))
