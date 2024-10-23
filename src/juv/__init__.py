"""Create, manage, and run reproducible Jupyter notebooks."""

from __future__ import annotations

import sys
import os
from pathlib import Path
import click

import rich


@click.group()
@click.version_option()
def cli():
    """Create, manage, and run reproducible Jupyter notebooks."""


@cli.command()
@click.option("--detail", is_flag=True)
def version(detail: bool) -> None:
    """Display juv's version."""
    from ._version import __version__

    print(f"juv {__version__}")
    if detail:
        from ._uv import uv

        result = uv(["version"], check=True)
        print(result.stdout.decode().strip())


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

    init(
        path=Path(file) if file else None,
        python=python,
        packages=[p for w in with_args for p in w.split(",")],
    )


@cli.command()
@click.argument("file", type=click.Path(exists=True), required=True)
@click.option("--requirements", "-r", type=click.Path(exists=True), required=False)
@click.argument("packages", nargs=-1)
def add(file: str, requirements: str | None, packages: tuple[str, ...]) -> None:
    """Add dependencies to the notebook."""
    from ._add import add

    add(path=Path(file), packages=packages, requirements=requirements)
    rich.print(f"Updated `[cyan]{Path(file).resolve().absolute()}[/cyan]`")


@cli.command()
@click.argument("file", type=click.Path(exists=True), required=True)
@click.option(
    "--jupyter",
    required=False,
    help="The Jupyter frontend to use. [env: JUV_JUPYTER=]",
)
@click.option("--with", "with_args", type=click.STRING, multiple=True)
@click.option("--python", type=click.STRING, required=False)
def run(
    file: str,
    jupyter: str | None,
    with_args: tuple[str, ...],
    python: str | None,
) -> None:
    """Launch a notebook or script."""

    from ._run import run

    run(
        path=Path(file),
        jupyter=jupyter,
        python=python,
        with_args=with_args,
    )


def upgrade_legacy_jupyter_command(args: list[str]) -> None:
    """Check legacy lab/notebook/nbclassic command usage and upgrade to 'run' with deprecation notice."""

    if len(args) >= 2:
        command = args[1]
        if (
            command.startswith("lab")
            or command.startswith("notebook")
            or command.startswith("nbclassic")
        ):
            rich.print(
                f"[bold]Warning:[/bold] The command '{command}' is deprecated. "
                f"Please use 'run' with `--jupyter={command}` or set JUV_JUPYTER={command}"
            )
            os.environ["JUV_JUPYTER"] = command
            args[1] = "run"


def main():
    upgrade_legacy_jupyter_command(sys.argv)
    cli()
