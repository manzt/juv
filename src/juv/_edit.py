import subprocess
import tempfile
from pathlib import Path

import jupytext

from ._cat import cat


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


def resolve_new_cells(previous_cells: list[dict], new_cells: list[dict]):
    for previous_cell, new_cell in zip(previous_cells, new_cells):
        new_cell["id"] = previous_cell["id"]
    return new_cells


def edit(path: Path, format_: str, editor: str) -> None:
    """Edit a Jupyter notebook in the specified format.

    Args:
        path: Path to notebook file
        format_: Target format ('markdown' or 'python')
        editor: Editor command to use

    """
    notebook = jupytext.read(path, fmt="ipynb")
    fmt = "md" if format_ == "markdown" else "py:percent"
    suffix = ".md" if fmt == "md" else ".py"

    text = open_editor(cat(notebook, fmt), suffix=suffix, editor=editor)

    new_notebook = jupytext.reads(text.strip(), fmt=fmt)
    notebook.cells = resolve_new_cells(notebook.cells, new_notebook.cells)

    path.write_text(jupytext.writes(notebook, fmt="ipynb"))
