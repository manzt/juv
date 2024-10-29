import subprocess
import tempfile
from pathlib import Path

import jupytext


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
        result = subprocess.run([editor, tpath], check=False)  # noqa: S603
        if result.returncode != 0:
            msg = f"Editor exited with code {result.returncode}"
            raise EditorAbortedError(msg)
        return tpath.read_text(encoding="utf-8")
    finally:
        tpath.unlink()


def edit(path: Path, format_: str, editor: str) -> None:
    """Edit a Jupyter notebook in the specified format.

    Args:
        path: Path to notebook file
        format_: Target format ('markdown' or 'python')
        editor: Editor command to use

    """
    contents = jupytext.read(path, fmt="ipynb")
    fmt = "md" if format_ == "markdown" else "py:percent"
    suffix = ".md" if fmt == "md" else ".py"
    contents = jupytext.writes(contents, fmt=fmt)

    text = open_editor(contents, suffix=suffix, editor=editor)

    # Only process the notebook if editor completed normally
    notebook = jupytext.reads(text, fmt=fmt)
    path.write_text(jupytext.writes(notebook, fmt="ipynb"))
