from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import typing
import tomllib
import sys

import rich
import jupytext

from ._nbconvert import write_ipynb, code_cell
from ._pep723 import parse_inline_script_metadata, extract_inline_meta


@dataclass
class Pep723Meta:
    dependencies: list[str]
    requires_python: str | None

    @classmethod
    def from_toml(cls, s: str) -> Pep723Meta:
        meta = tomllib.loads(s)
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
    return kind in ["notebook", "lab", "nbclassic"]


def parse_notebook_specifier(value: str | None) -> Runtime:
    value = value or os.getenv("JUV_JUPYTER", "lab")
    match value.split("@"):
        case [kind, version] if is_notebook_kind(kind):
            return Runtime(kind, version)
        case [kind] if is_notebook_kind(kind):
            return Runtime(kind)

    raise ValueError(f"Invalid runtime specifier: {value}")


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
    match fp.suffix:
        case ".py":
            nb = load_script_notebook(fp)
        case ".ipynb":
            nb = jupytext.read(fp, fmt="ipynb")
        case _:
            raise ValueError(f"Unsupported file extension: {fp.suffix}")

    meta = next(
        (
            parse_inline_script_metadata("".join(cell["source"]))
            for cell in filter(lambda c: c["cell_type"] == "code", nb.get("cells", []))
        ),
        None,
    )

    return meta, nb


def prepare_uvx_args(
    target: Path,
    runtime: Runtime,
    pep723_meta: Pep723Meta | None,
    python: str | None,
    with_args: typing.Sequence[str],
) -> list[str]:
    args = ["--with=setuptools"]

    for with_arg in with_args:
        args.append(f"--with={with_arg}")

    if python:
        args.append(f"--python={python}")

    if pep723_meta:
        # only add --python if not specified by user and present in meta
        if pep723_meta.requires_python and not python:
            args.append(f"--python={pep723_meta.requires_python}")

        if len(pep723_meta.dependencies) > 0:
            args.append(f"--with={','.join(pep723_meta.dependencies)}")

    version = runtime.version

    match runtime.name:
        case "lab":
            args.append(f"--with=jupyterlab{'==' + version if version else ''}")
        case "notebook":
            args.append(f"--with=notebook{'==' + version if version else ''}")
        case "nbclassic":
            args.append(f"--with=nbclassic{'==' + version if version else ''}")

    args.extend(["--from=jupyter-core", "jupyter", runtime.name, str(target)])
    return args


def run(
    path: Path,
    jupyter: str | None,
    python: str | None,
    with_args: typing.Sequence[str],
) -> None:
    """Launch a notebook or script."""
    runtime = parse_notebook_specifier(jupyter)
    meta, nb = to_notebook(path)

    if path.suffix == ".py":
        path = path.with_suffix(".ipynb")
        write_ipynb(nb, path)
        rich.print(
            f"Converted script to notebook `[cyan]{path.resolve().absolute()}[/cyan]`"
        )

    meta = Pep723Meta.from_toml(meta) if meta else None

    try:
        os.execvp("uvx", prepare_uvx_args(path, runtime, meta, python, with_args))
    except OSError as e:
        rich.print(f"Error executing [cyan]uvx[/cyan]: {e}", file=sys.stderr)
        sys.exit(1)
