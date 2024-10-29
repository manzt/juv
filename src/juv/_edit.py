import os
import subprocess
import tempfile
from pathlib import Path

import jupytext


def open_editor(contents: str, suffix: str, editor: str) -> str:
    """Open an editor with the given contents and return the modified text."""
    with tempfile.NamedTemporaryFile(
        suffix=suffix, mode="w+", delete=False, encoding="utf-8"
    ) as tf:
        # Write initial text if provided
        if contents:
            tf.write(contents)
            tf.flush()

        temp_filename = tf.name

    try:
        subprocess.call([editor, temp_filename])

        return Path(temp_filename).read_text(encoding="utf-8")

    finally:
        # Clean up the temporary file
        Path(temp_filename).unlink()


def edit(path: Path, format_: str, editor: str) -> None:
    contents = jupytext.read(path, fmt="ipynb")
    fmt = "md" if format_ == "markdown" else "py:percent"
    suffix = ".md" if fmt == "md" else ".py"
    contents = jupytext.writes(contents, fmt=fmt)
    text = open_editor(contents, suffix=suffix, editor=editor)
    notebook = jupytext.reads(text, fmt=fmt)
    path.write_text(jupytext.writes(notebook, fmt="ipynb"))
