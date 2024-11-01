"""Create, manage, and run reproducible Jupyter notebooks."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
import rich


@click.group()
@click.version_option()
def cli() -> None:
    """Create, manage, and run reproducible Jupyter notebooks."""


@cli.command()
@click.option("--output-format", type=click.Choice(["json", "text"]))
def version(output_format: str | None) -> None:
    """Display juv's version."""
    from ._version import __version__

    if output_format == "json":
        sys.stdout.write(f'{{"version": "{__version__}"}}\n')
    else:
        sys.stdout.write(f"juv {__version__}\n")


@cli.command()
@click.argument("file", type=click.Path(exists=False), required=False)
@click.option("--with", "with_args", type=click.STRING, multiple=True)
@click.option("--python", type=click.STRING, required=False)
def init(
    file: str | None,
    with_args: tuple[str, ...],
    python: str | None,
) -> None:
    """Initialize a new notebook."""
    from ._init import init

    path = init(
        path=Path(file) if file else None,
        python=python,
        packages=[p for w in with_args for p in w.split(",")],
    )
    path = os.path.relpath(path.resolve(), Path.cwd())
    rich.print(f"Initialized notebook at `[cyan]{path}[/cyan]`")


@cli.command()
@click.argument("file", type=click.Path(exists=True), required=True)
@click.option("--requirements", "-r", type=click.Path(exists=True), required=False)
@click.option("--extra", "extras", type=click.STRING, multiple=True)
@click.option("--editable", is_flag=True)
@click.argument("packages", nargs=-1)
def add(
    file: str,
    requirements: str | None,
    extras: tuple[str, ...],
    packages: tuple[str, ...],
    *,
    editable: bool,
) -> None:
    """Add dependencies to a notebook."""
    from ._add import add

    add(
        path=Path(file),
        packages=packages,
        requirements=requirements,
        extras=extras,
        editable=editable,
    )
    path = os.path.relpath(Path(file).resolve(), Path.cwd())
    rich.print(f"Updated `[cyan]{path}[/cyan]`")


@cli.command()
@click.argument("file", type=click.Path(exists=True), required=True)
@click.option(
    "--jupyter",
    required=False,
    help="The Jupyter frontend to use. [env: JUV_JUPYTER=]",
)
@click.option("--with", "with_args", type=click.STRING, multiple=True)
@click.option("--python", type=click.STRING, required=False)
@click.argument(
    "jupyter_args", nargs=-1, type=click.UNPROCESSED
)  # Capture all args after --
def run(
    file: str,
    jupyter: str | None,
    with_args: tuple[str, ...],
    python: str | None,
    jupyter_args: tuple[str, ...],
) -> None:
    """Launch a notebook or script in a Jupyter front end."""
    from ._run import run

    run(
        path=Path(file),
        jupyter=jupyter,
        python=python,
        with_args=with_args,
        jupyter_args=jupyter_args,
    )


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True), required=True)
def clear(files: list[str]) -> None:
    """Clear notebook cell outputs.

    Supports multiple files and glob patterns (e.g., *.ipynb, notebooks/*.ipynb)
    """
    from ._clear import clear

    paths = []
    for arg in files:
        path = Path(arg)
        to_check = path.glob("*.ipynb") if path.is_dir() else [path]

        for path in to_check:
            if not path.is_file():
                continue

            if path.suffix != ".ipynb":
                rich.print(
                    f"[bold yellow]Warning:[/bold yellow] Skipping "
                    f"`[cyan]{path}[/cyan]` because it is not a notebook",
                    file=sys.stderr,
                )
                continue

            paths.append(path)

    if len(paths) == 1:
        clear(paths[0])
        path = os.path.relpath(paths[0].resolve(), Path.cwd())
        rich.print(f"Cleared output from `[cyan]{path}[/cyan]`", file=sys.stderr)
        return

    for path in paths:
        clear(path)
        rich.print(path.resolve().absolute())

    rich.print(f"Cleared output from {len(paths)} notebooks", file=sys.stderr)


@cli.command()
@click.argument("notebook", type=click.Path(exists=True), required=True)
@click.option("--editor", type=click.STRING, required=False)
def edit(notebook: str, editor: str | None) -> None:
    """Quick edit a notebook as markdown."""
    from ._edit import EditorAbortedError, edit

    if editor is None:
        editor = os.environ.get("EDITOR")

    if editor is None:
        msg = (
            "No editor specified. Please set the EDITOR environment variable "
            "or use the --editor option."
        )
        rich.print(f"[bold red]Error:[/bold red] {msg}", file=sys.stderr)
        return

    path = Path(notebook)
    if path.suffix != ".ipynb":
        rich.print(
            f"[bold red]Error:[/bold red] `[cyan]{path}[/cyan]` is not a notebook",
            file=sys.stderr,
        )
        return

    try:
        edit(path=path, editor=editor)
        rich.print(f"Edited `[cyan]{notebook}[/cyan]`")
    except EditorAbortedError as e:
        rich.print(f"[bold red]Error:[/bold red] {e}", file=sys.stderr)


def upgrade_legacy_jupyter_command(args: list[str]) -> None:
    """Check legacy command usage and upgrade to 'run' with deprecation notice."""
    if len(args) >= 2:  # noqa: PLR2004
        command = args[1]
        if command.startswith(("lab", "notebook", "nbclassic")):
            rich.print(
                f"[bold]Warning:[/bold] The command '{command}' is deprecated. "
                f"Please use 'run' with `--jupyter={command}` "
                f"or set JUV_JUPYTER={command}",
            )
            os.environ["JUV_JUPYTER"] = command
            args[1] = "run"


@cli.command("exec")
@click.argument("notebook", type=click.Path(exists=True), required=True)
@click.option("--python", type=click.STRING, required=False)
@click.option("--with", "with_args", type=click.STRING, multiple=True)
@click.option("--quiet", is_flag=True)
def exec_(
    notebook: str, python: str | None, with_args: tuple[str, ...], *, quiet: bool
) -> None:
    """Execute a notebook as a script."""
    from ._exec import exec_

    exec_(path=Path(notebook), python=python, with_args=with_args, quiet=quiet)


@cli.command()
@click.argument("notebook", type=click.Path(exists=True), required=True)
@click.option("--script", is_flag=True)
def cat(notebook: str, *, script: bool) -> None:
    """Print notebook contents to stdout."""
    from ._cat import cat

    path = Path(notebook)
    if path.suffix != ".ipynb":
        rich.print(
            f"[bold red]Error:[/bold red] `[cyan]{path}[/cyan]` is not a notebook",
            file=sys.stderr,
        )
        return

    sys.stdout.write(cat(path, script=script))


def main() -> None:
    """Run the CLI."""
    upgrade_legacy_jupyter_command(sys.argv)
    cli()
