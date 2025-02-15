from __future__ import annotations

import tempfile
import typing
from pathlib import Path

import jupytext
from jupytext.pandoc import subprocess
from uv import find_uv_bin

from ._nbutils import code_cell, write_ipynb
from ._pep723 import includes_inline_metadata
from ._utils import find
from ._uv import uv


def uv_pip_compile(
    packages: typing.Sequence[str],
    requirements: str | None,
    *,
    no_deps: bool,
    exclude_newer: str | None,
) -> list[str]:
    """Use `pip compile` to generate exact versions of packages."""
    requirements_txt = (
        "" if requirements is None else Path(requirements).read_text(encoding="utf-8")
    )

    # just append the packages on to the requirements
    for package in packages:
        if package not in requirements_txt:
            requirements_txt += f"{package}\n"

    result = subprocess.run(
        [
            find_uv_bin(),
            "pip",
            "compile",
            *(["--no-deps"] if no_deps else []),
            *([f"--exclude-newer={exclude_newer}"] if exclude_newer else []),
            "-",
        ],
        input=requirements_txt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode())

    # filter only for the exact versions
    return [pkg for pkg in result.stdout.decode().split("\n") if "==" in pkg]


def uv_script(  # noqa: PLR0913
    script: Path | str,
    *,
    packages: typing.Sequence[str],
    requirements: str | None,
    extras: typing.Sequence[str] | None,
    editable: bool,
    branch: str | None,
    rev: str | None,
    tag: str | None,
    exclude_newer: str | None,
    index: str | None,
    default_index: str | None,
) -> None:
    uv(
        [
            "add",
            *(["--requirements", requirements] if requirements else []),
            *([f"--extra={extra}" for extra in extras or []]),
            *(["--editable"] if editable else []),
            *([f"--tag={tag}"] if tag else []),
            *([f"--branch={branch}"] if branch else []),
            *([f"--rev={rev}"] if rev else []),
            *([f"--exclude-newer={exclude_newer}"] if exclude_newer else []),
            *([f"--index={index}"] if index else []),
            *([f"--default-index={default_index}"] if default_index else []),
            "--script",
            str(script),
            *packages,
        ],
        check=True,
    )


def add_notebook(  # noqa: PLR0913
    path: Path,
    *,
    packages: typing.Sequence[str],
    requirements: str | None,
    extras: typing.Sequence[str] | None,
    editable: bool,
    branch: str | None,
    rev: str | None,
    tag: str | None,
    exclude_newer: str | None,
    index: str | None,
    default_index: str | None,
) -> None:
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

        uv_script(
            script=f.name,
            packages=packages,
            requirements=requirements,
            extras=extras,
            editable=editable,
            branch=branch,
            rev=rev,
            tag=tag,
            exclude_newer=exclude_newer,
            index=index,
            default_index=default_index,
        )
        f.seek(0)
        cell["source"] = f.read().strip()

        if lockfile.exists():
            notebook["metadata"]["uv.lock"] = lockfile.read_text(encoding="utf-8")
            lockfile.unlink(missing_ok=True)

    write_ipynb(notebook, path.with_suffix(".ipynb"))


def add(  # noqa: PLR0913
    *,
    path: Path,
    packages: typing.Sequence[str],
    requirements: str | None = None,
    extras: typing.Sequence[str] | None = None,
    tag: str | None = None,
    branch: str | None = None,
    rev: str | None = None,
    pin: bool = False,
    editable: bool = False,
    exclude_newer: str | None = None,
    index: str | None = None,
    default_index: str | None = None,
) -> None:
    if pin:
        packages = uv_pip_compile(
            packages, requirements, exclude_newer=exclude_newer, no_deps=True
        )
        requirements = None

    (add_notebook if path.suffix == ".ipynb" else uv_script)(
        path,
        packages=packages,
        requirements=requirements,
        extras=extras,
        editable=editable,
        branch=branch,
        rev=rev,
        tag=tag,
        exclude_newer=exclude_newer,
        index=index,
        default_index=default_index,
    )
