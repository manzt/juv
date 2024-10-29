import re
import subprocess
import tempfile
from pathlib import Path

import jupytext


class EditorAbortedError(Exception):
    """Exception raised when the editor exits abnormally."""


def strip_markdown_header(content: str) -> tuple[str, str]:
    # Match content between first set of --- markers
    match = re.match(r"^---\n.*?\n---\n(.*)$", content, re.DOTALL)
    if match:
        header = content[: content.find(match.group(1))]
        return header, match.group(1)
    return "", content


def strip_python_frontmatter_comment(content: str) -> tuple[str, str]:
    """Remove frontmatter comment block from beginning of Python script.

    Looks for content between # --- markers at start of file.

    Args:
        content: Full content of Python file

    Returns:
        tuple[str, str]: (frontmatter, remaining_content)

    """
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "# ---":
        return "", content

    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "# ---":
            return "".join(lines[: i + 1]), "".join(lines[i + 1 :])

    return "", content


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

    contents = jupytext.writes(notebook, fmt=fmt)

    if fmt == "md":
        _, contents = strip_markdown_header(contents)
    else:
        _, contents = strip_python_frontmatter_comment(contents)

    text = open_editor(contents.strip(), suffix=suffix, editor=editor)

    notebook = jupytext.reads(text.strip(), fmt=fmt)
    path.write_text(jupytext.writes(notebook, fmt="ipynb"))
