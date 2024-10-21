"""A wrapper around `uv` to launch ephemeral Jupyter notebooks."""

from __future__ import annotations

import pathlib
import re
import tomllib
import dataclasses
import sys
import shutil
import os
import tempfile
import subprocess
from pathlib import Path
import typing
import click

import rich
import jupytext
from nbformat.v4.nbbase import new_code_cell, new_notebook


@dataclasses.dataclass
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


@dataclasses.dataclass
class Runtime:
    name: RuntimeName
    version: str | None = None


RuntimeName = typing.Literal["notebook", "lab", "nbclassic"]

REGEX = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"


def parse_inline_script_metadata(script: str) -> str | None:
    name = "script"
    matches = list(
        filter(lambda m: m.group("type") == name, re.finditer(REGEX, script))
    )
    if len(matches) > 1:
        raise ValueError(f"Multiple {name} blocks found")
    elif len(matches) == 1:
        content = "".join(
            line[2:] if line.startswith("# ") else line[1:]
            for line in matches[0].group("content").splitlines(keepends=True)
        )
        return content
    else:
        return None


def nbcell(source: str, hidden: bool = False) -> dict:
    return new_code_cell(
        source,
        metadata={"jupyter": {"source_hidden": hidden}},
    )


def load_script_notebook(fp: pathlib.Path) -> dict:
    script = fp.read_text()
    inline_meta = None
    if meta_block := re.search(REGEX, script):
        inline_meta = meta_block.group(0)
        script = script.replace(inline_meta, "")
    nb = jupytext.reads(script.strip())
    if inline_meta:
        nb["cells"].insert(
            0,
            nbcell(inline_meta.strip(), hidden=True),
        )
    return nb


def to_notebook(fp: pathlib.Path) -> tuple[str | None, dict]:
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


def assert_uv_available():
    if shutil.which("uv") is None:
        rich.print("Error: 'uv' command not found.", file=sys.stderr)
        rich.print("Please install 'uv' to run `juv`.", file=sys.stderr)
        rich.print(
            "For more information, visit: https://github.com/astral-sh/uv",
            file=sys.stderr,
        )
        sys.exit(1)


def create_uv_run_command(
    target: pathlib.Path,
    runtime: Runtime,
    pep723_meta: Pep723Meta | None,
    pre_args: list[str],
) -> list[str]:
    cmd = ["uvx", "--from=jupyter-core", "--with=setuptools"]

    if pep723_meta:
        # only add --python if not specified by user and present in meta
        if pep723_meta.requires_python and not any(
            x.startswith("--python") for x in pre_args
        ):
            cmd.append(f"--python={pep723_meta.requires_python}")

        if len(pep723_meta.dependencies) > 0:
            cmd.append(f"--with={','.join(pep723_meta.dependencies)}")

    version = runtime.version

    match runtime.name:
        case "lab":
            cmd.append(f"--with=jupyterlab{'==' + version if version else ''}")
        case "notebook":
            cmd.append(f"--with=notebook{'==' + version if version else ''}")
        case "nbclassic":
            cmd.append(f"--with=nbclassic{'==' + version if version else ''}")

    cmd.extend([*pre_args, "jupyter", runtime.name, str(target)])
    return cmd


def update_or_add_inline_meta(
    nb: dict,
    deps: typing.Sequence[str],
    dir: pathlib.Path,
    uv_flags: typing.Sequence[str],
) -> None:
    def includes_inline_meta(cell: dict) -> bool:
        return cell["cell_type"] == "code" and (
            re.search(REGEX, "".join(cell["source"])) is not None
        )

    with tempfile.NamedTemporaryFile(
        mode="w+",
        delete=True,
        suffix=".py",
        dir=dir,
    ) as f:
        cell = next(
            (cell for cell in nb["cells"] if includes_inline_meta(cell)),
            None,
        )
        if cell is None:
            nb["cells"].insert(0, nbcell("", hidden=True))
            cell = nb["cells"][0]

        f.write(cell["source"].strip())
        f.flush()
        subprocess.run(["uv", "add", "--quiet", *uv_flags, "--script", f.name, *deps])
        f.seek(0)
        cell["source"] = f.read().strip()


def init_notebook(uv_args: list[str], dir: pathlib.Path) -> dict:
    with tempfile.NamedTemporaryFile(
        mode="w+",
        suffix=".py",
        delete=True,
        dir=dir,
    ) as f:
        subprocess.run(["uv", "init", "--quiet", "--script", f.name, *uv_args])
        f.seek(0)
        contents = f.read().strip()
        nb = new_notebook(cells=[nbcell(contents, hidden=True)])
    return nb


def write_nb(nb: dict, file: pathlib.Path) -> None:
    file.write_text(jupytext.writes(nb, fmt="ipynb"))


def get_untitled() -> pathlib.Path:
    if not pathlib.Path("Untitled.ipynb").exists():
        return pathlib.Path("Untitled.ipynb")

    for i in range(1, 100):
        file = pathlib.Path(f"Untitled{i}.ipynb")
        if not file.exists():
            return file

    raise ValueError("Could not find an available UntitledX.ipynb")


def is_notebook_kind(kind: str) -> typing.TypeGuard[RuntimeName]:
    return kind in ["notebook", "lab", "nbclassic"]


def parse_notebook_specifier(value: str | None) -> Runtime:
    match (value or "").split("@"):
        case [kind, version] if is_notebook_kind(kind):
            return Runtime(kind, version)
        case [kind] if is_notebook_kind(kind):
            return Runtime(kind)

    kind = os.getenv("JUV_NOTEBOOK", "lab")
    if not is_notebook_kind(kind):
        raise click.BadParameter(f"Invalid notebook kind: {kind}")

    return Runtime(kind, None)


@click.group()
def cli(): ...


@cli.command()
def version() -> None:
    """Display juv's version."""
    import importlib.metadata

    print(f"juv {importlib.metadata.version('juv')}")


@cli.command()
def info():
    """Display juv and uv versions."""
    import importlib.metadata

    print(f"juv {importlib.metadata.version('juv')}")
    uv_version = subprocess.run(["uv", "version"], capture_output=True, text=True)
    print(uv_version.stdout)


@cli.command()
@click.argument("file", type=click.Path(exists=False), required=False)
@click.option("--python", type=click.STRING, required=False)
def init(
    file: str,
    python: str | None,
) -> None:
    """Initialize a new notebook."""
    path = Path(file) if file else None
    if not path:
        path = get_untitled()
    if not path.suffix == ".ipynb":
        rich.print("File must have a `[cyan].ipynb[/cyan]` extension.", file=sys.stderr)
        sys.exit(1)
    uv_args = []
    if python:
        uv_args.extend(["--python", python])
    nb = init_notebook(uv_args, path.parent)
    write_nb(nb, path)
    rich.print(f"Initialized notebook at `[cyan]{path.resolve().absolute()}[/cyan]`")


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("file", type=click.Path(exists=True), required=True)
@click.option("--requirements", "-r", type=click.Path(exists=True), required=False)
@click.argument("packages", nargs=-1)
def add(file: str, requirements: str | None, packages: tuple[str, ...]) -> None:
    """Add dependencies to the notebook."""
    path = Path(file)
    _, nb = to_notebook(path)
    uv_args = []
    if requirements:
        uv_args.extend(["--requirements", requirements])
    update_or_add_inline_meta(nb, packages, path.parent, uv_args)
    write_nb(nb, path.with_suffix(".ipynb"))
    rich.print(f"Updated `[cyan]{path.resolve().absolute()}[/cyan]`")


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("file", type=click.Path(exists=True), required=True)
@click.option(
    "--notebook",
    "-n",
    required=False,
    help="The notebook runner the run environment. [env: JUV_NOTEBOOK=]",
)
@click.option("--with", "with_args", type=click.STRING, multiple=True)
@click.option("--python", type=click.STRING, required=False)
def run(
    file: str,
    notebook: str | None,
    with_args: tuple[str, ...],
    python: str | None,
) -> None:
    """Launch a notebook or script."""
    runtime = parse_notebook_specifier(notebook)
    path = Path(file)
    meta, nb = to_notebook(path)

    if path.suffix == ".py":
        path = path.with_suffix(".ipynb")
        write_nb(nb, path)
        rich.print(
            f"Converted script to notebook `[cyan]{path.resolve().absolute()}[/cyan]`"
        )

    meta = Pep723Meta.from_toml(meta) if meta else None

    uv_flags = []
    for arg in with_args:
        uv_flags.extend(["--with", arg])
    if python:
        uv_flags.extend(["--python", python])

    cmd = create_uv_run_command(path, runtime, meta, uv_flags)
    try:
        os.execvp(cmd[0], cmd)
    except OSError as e:
        print(f"Error executing {cmd[0]}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    cli()
