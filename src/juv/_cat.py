from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

import jupytext

if TYPE_CHECKING:
    from pathlib import Path


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


def notebook_contents(nb: Path | dict, *, script: bool) -> str:
    fmt = "py:percent" if script else "md"
    notebook = nb if isinstance(nb, dict) else jupytext.read(nb)
    contents = jupytext.writes(notebook, fmt=fmt)
    if script:
        _, contents = strip_python_frontmatter_comment(contents)
    else:
        _, contents = strip_markdown_header(contents)
    return contents.lstrip()


def cat(path: Path, *, script: bool, pager: str | None = None) -> None:
    code = notebook_contents(path, script=script)

    if not pager:
        sys.stdout.write(code)
        return

    import os
    import subprocess

    command = [pager]

    # special case bat to apply syntax highlighting
    if pager == "bat":
        ext = "md" if not script else "py"
        command.extend(
            [
                f"--language={ext}",
                f"--file-name={path.stem}.{ext}",
            ]
        )

    subprocess.run(  # noqa: PLW1510, S603
        command,
        input=code.encode(),
        stdout=sys.stdout,
        stderr=sys.stderr,
        env=os.environ,
    )
