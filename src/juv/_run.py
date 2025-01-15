from __future__ import annotations

import os
import typing

import jupytext
import rich

from ._nbutils import code_cell, write_ipynb
from ._pep723 import extract_inline_meta
from ._run_template import Runtime, prepare_run_script_and_uv_run_args

if typing.TYPE_CHECKING:
    from pathlib import Path


def load_script_notebook(fp: Path) -> dict:
    script = fp.read_text(encoding="utf-8")
    # we could read the whole thing with jupytext,
    # but is nice to ensure the script meta is at the top in it's own
    # cell (that we can hide by default in JupyterLab)
    inline_meta, script = extract_inline_meta(script)
    notebook = jupytext.reads(script.strip())
    if inline_meta:
        inline_meta_cell = code_cell(inline_meta.strip(), hidden=True)
        notebook["cells"].insert(0, inline_meta_cell)
    return notebook


def to_notebook(fp: Path) -> tuple[str | None, dict]:
    if fp.suffix == ".py":
        nb = load_script_notebook(fp)
    elif fp.suffix == ".ipynb":
        nb = jupytext.read(fp, fmt="ipynb")
    else:
        msg = f"Unsupported file extension: {fp.suffix}"
        raise ValueError(msg)

    for cell in filter(lambda c: c["cell_type"] == "code", nb.get("cells", [])):
        meta, _ = extract_inline_meta("".join(cell["source"]))
        if meta:
            return meta, nb

    return None, nb


def run(  # noqa: PLR0913
    *,
    path: Path,
    jupyter: str,
    python: str | None,
    with_args: typing.Sequence[str],
    jupyter_args: typing.Sequence[str],
    mode: str,
) -> None:
    """Launch a notebook or script."""
    runtime = Runtime.try_from_specifier(jupyter)
    meta, nb = to_notebook(path)
    lockfile_contents = nb.get("metadata", {}).get("uv.lock")

    if path.suffix == ".py":
        path = path.with_suffix(".ipynb")
        write_ipynb(nb, path)
        rich.print(
            f"Converted script to notebook `[cyan]{path.resolve().absolute()}[/cyan]`",
        )

    target = path.resolve()

    script, args = prepare_run_script_and_uv_run_args(
        runtime=runtime,
        target=target,
        meta=meta or "",
        python=python,
        with_args=with_args,
        jupyter_args=jupyter_args,
        no_project=True,
        mode=mode,
    )

    # change to the directory of the script/notebook before running uv
    os.chdir(target.parent)

    if mode == "dry":
        print(f"uv {' '.join(args)}")  # noqa: T201

    elif mode == "managed":
        from ._run_managed import run as run_managed

        run_managed(
            script=script,
            args=args,
            filename=str(path),
            lockfile_contents=lockfile_contents,
            dir=target.parent,
        )
    else:
        from ._run_replace import run as run_replace

        run_replace(
            script=script,
            args=args,
            lockfile_contents=lockfile_contents,
            dir=target.parent,
        )
