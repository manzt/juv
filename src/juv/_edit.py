import difflib
import operator
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


def edit(path: Path, editor: str) -> None:
    """Edit a Jupyter notebook as markdown.

    Args:
        path: Path to notebook file
        editor: Editor command to use

    """
    prev_notebook = jupytext.read(path, fmt="ipynb")

    text = open_editor(cat(prev_notebook, script=False), suffix=".md", editor=editor)
    new_notebook = jupytext.reads(text.strip(), fmt="md")

    apply_diff(prev_notebook["cells"], new_notebook["cells"])

    # replace the original notebook cells with the modified ones
    prev_notebook["cells"] = new_notebook["cells"]
    path.write_text(jupytext.writes(prev_notebook, fmt="ipynb"))


def apply_diff(
    prev_cells: list[dict], new_cells: list[dict], min_similarity: float = 0.8
) -> None:
    """Intelligently diff and merge cells to minimize changes.

    Args:
        prev_cells: Original notebook cells
        new_cells: Modified notebook cells
    Returns:
        List of merged cells with minimal changes.

    """
    prev_cells = prev_cells.copy()

    def update(prev: dict, new: dict) -> None:
        if "id" in prev:
            new["id"] = prev["id"]
        if "outputs" in prev:
            new["outputs"] = prev["outputs"]
        if "execution_count" in prev:
            new["execution_count"] = prev["execution_count"]

    for new in new_cells:
        scores: list[tuple[float, dict]] = []
        for prev in prev_cells:
            matcher = difflib.SequenceMatcher(
                isjunk=None, a="".join(new["source"]), b="".join(prev["source"])
            )
            score = matcher.ratio()
            if score == 1.0:
                # we have an exact match and can skip the rest
                prev_cells.remove(prev)
                update(prev, new)
                break
            scores.append((score, prev))
        if scores:
            score, prev = max(scores, key=operator.itemgetter(0))
            if score > min_similarity:  # only update if similarity is high enough
                prev_cells.remove(prev)
                update(prev, new)
