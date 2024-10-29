from __future__ import annotations

import re
from pathlib import Path

import jupytext


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


def cat(nb: Path | dict, fmt: str) -> str:
    fmt = {"markdown": "md", "py:percent": "py", "md": "md", "py": "py"}[fmt]
    notebook = nb if isinstance(nb, dict) else jupytext.read(nb)
    contents = jupytext.writes(notebook, fmt=fmt)
    if fmt == "md":
        _, contents = strip_markdown_header(contents)
    else:
        _, contents = strip_python_frontmatter_comment(contents)
    return contents.lstrip()
