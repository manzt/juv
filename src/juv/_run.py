from __future__ import annotations

import os
import sys
import typing
from dataclasses import dataclass

import jupytext
import rich
from uv import find_uv_bin

from ._nbutils import code_cell, write_ipynb
from ._pep723 import extract_inline_meta, parse_inline_script_metadata

if typing.TYPE_CHECKING:
    from pathlib import Path


@dataclass
class Pep723Meta:
    dependencies: list[str]
    requires_python: str | None

    @classmethod
    def from_toml(cls, s: str) -> Pep723Meta:
        # tomllib introduced in 3.11
        if sys.version_info < (3, 11):
            import toml
        else:
            import tomllib as toml
        meta = toml.loads(s)
        return cls(
            dependencies=meta.get("dependencies", []),
            requires_python=meta.get("requires_python", None),
        )


@dataclass
class Runtime:
    name: RuntimeName
    version: str | None = None


RuntimeName = typing.Literal["notebook", "lab", "nbclassic"]


def is_notebook_kind(kind: str) -> typing.TypeGuard[RuntimeName]:
    return kind in {"notebook", "lab", "nbclassic"}


def parse_notebook_specifier(value: str | None) -> Runtime:
    value = value or os.getenv("JUV_JUPYTER", "lab")

    parts = value.split("@")

    if len(parts) == 2 and is_notebook_kind(parts[0]):  # noqa: PLR2004
        return Runtime(parts[0], parts[1])

    if len(parts) == 1 and is_notebook_kind(parts[0]):
        return Runtime(parts[0])

    msg = f"Invalid runtime specifier: {value}"
    raise ValueError(msg)


def load_script_notebook(fp: Path) -> dict:
    script = fp.read_text()
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

    meta = next(
        (
            parse_inline_script_metadata("".join(cell["source"]))
            for cell in filter(lambda c: c["cell_type"] == "code", nb.get("cells", []))
        ),
        None,
    )

    return meta, nb


def get_juv_extras(
    jupyter: typing.Literal["notebook", "lab", "nbclassic"],
    version: str | None = None,
) -> list[str]:
    jupyter_dependency = {
        "notebook": "notebook",
        "lab": "jupyterlab",
        "nbclassic": "nbclassic",
    }[jupyter]
    if version:
        jupyter_dependency += f"=={version}"
    packages = [
        "setuptools",
        jupyter_dependency,
    ]
    if os.environ.get("JUV_CELLMAGIC") == "1":
        from ._wheel import get_juv_jupyter_wheel

        # adds %juv magic to the notebook env
        packages.append(str(get_juv_jupyter_wheel()))

    return packages


def prepare_uv_tool_run(
    target: Path,
    runtime: Runtime,
    meta: Pep723Meta,
    python: str | None,
    extra_with_args: typing.Sequence[str],
    *,
    no_cache: bool = False,
    no_project: bool = False,
) -> tuple[str, list[str], dict]:
    juv_with_args = get_juv_extras(runtime.name, runtime.version)

    if meta.requires_python and python is None:
        python = meta.requires_python

    uv = os.fsdecode(find_uv_bin())
    args = [
        "tool",
        "run",
        "--isolated",
        *(["--no-project"] if no_project else []),
        *(["--no-cache"] if no_cache else []),
        *([f"--python={python}"] if python else []),
        "--with=" + ",".join(juv_with_args),
        *(["--with=" + ",".join(meta.dependencies)] if meta.dependencies else []),
        *(["--with=" + ",".join(extra_with_args)] if extra_with_args else []),
        "jupyter",
        runtime.name,
        str(target),
    ]
    env = os.environ.copy()
    env["JUV_INTERNAL__UV"] = uv
    env["JUV_INTERNAL__NOTEBOOK_TARGET"] = str(target.resolve())
    env["JUV_INTERNAL__NOTEBOOK_EXTRAS"] = ",".join(juv_with_args)
    return uv, args, env


def run(
    path: Path,
    jupyter: str | None,
    python: str | None,
    with_args: typing.Sequence[str],
    *,
    no_cache: bool,
    no_project: bool,
) -> None:
    """Launch a notebook or script."""
    runtime = parse_notebook_specifier(jupyter)
    meta, nb = to_notebook(path)

    if path.suffix == ".py":
        path = path.with_suffix(".ipynb")
        write_ipynb(nb, path)
        rich.print(
            f"Converted script to notebook `[cyan]{path.resolve().absolute()}[/cyan]`",
        )

    uv, args, env = prepare_uv_tool_run(
        target=path,
        runtime=runtime,
        meta=Pep723Meta.from_toml(meta) if meta else Pep723Meta([], None),
        python=python,
        extra_with_args=with_args,
        no_cache=no_cache,
        no_project=no_project,
    )

    if os.environ.get("JUV_RUN_MODE") == "managed":
        from ._run_managed import run as run_managed

        run_managed(uv, args, path.name, runtime.name, runtime.version, env=env)
    else:
        try:
            os.execvpe(uv, args, env=env)  # noqa: S606
        except OSError as e:
            rich.print(f"Error executing [cyan]uvx[/cyan]: {e}", file=sys.stderr)
            sys.exit(1)
