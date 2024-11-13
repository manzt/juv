"""Create, manage, and run reproducible Jupyter notebooks."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
import rich
from rich.console import Console


@click.group()
@click.version_option()
def cli() -> None:
    """Create, manage, and run reproducible Jupyter notebooks."""


@cli.command()
@click.option(
    "--output-format",
    type=click.Choice(["json", "text"]),
    help="Output format [default: text]",
)
def version(output_format: str | None) -> None:
    """Display juv's version."""
    from ._version import __version__

    if output_format == "json":
        sys.stdout.write(f'{{"version": "{__version__}"}}\n')
    else:
        sys.stdout.write(f"juv {__version__}\n")


@cli.command()
@click.argument("file", type=click.Path(exists=False), required=False)
@click.option("--with", "with_args", type=click.STRING, multiple=True, hidden=True)
@click.option(
    "--python",
    "-p",
    type=click.STRING,
    required=False,
    help="The Python interpreter to use to determine the minimum supported Python version. [env: UV_PYTHON=]",  # noqa: E501
)
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
@click.option(
    "--requirements",
    "-r",
    type=click.Path(exists=True),
    required=False,
    help="Add all packages listed in the given `requirements.txt` file.",
)
@click.option(
    "--extra",
    "extras",
    type=click.STRING,
    multiple=True,
    help="Extras to enable for the dependency. May be provided more than once.",
)
@click.option("--editable", is_flag=True, help="Add the requirements as editable.")
@click.option(
    "--tag", type=click.STRING, help="Tag to use when adding a dependency from Git."
)
@click.option(
    "--branch",
    type=click.STRING,
    help="Branch to use when adding a dependency from Git.",
)
@click.option(
    "--rev", type=click.STRING, help="Commit to use when adding a dependency from Git."
)
@click.argument("packages", nargs=-1)
def add(  # noqa: PLR0913
    *,
    file: str,
    requirements: str | None,
    extras: tuple[str, ...],
    packages: tuple[str, ...],
    tag: str | None,
    branch: str | None,
    rev: str | None,
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
        tag=tag,
        branch=branch,
        rev=rev,
    )
    path = os.path.relpath(Path(file).resolve(), Path.cwd())
    rich.print(f"Updated `[cyan]{path}[/cyan]`")


@cli.command()
@click.argument("file", type=click.Path(exists=True), required=True)
@click.option(
    "--jupyter",
    required=False,
    help="The Jupyter frontend to use. [env: JUV_JUPYTER=]",
    default=lambda: os.environ.get("JUV_JUPYTER", "lab"),
)
@click.option(
    "--with",
    "with_args",
    type=click.STRING,
    multiple=True,
    help="Run with the given packages installed.",
)
@click.option(
    "--python",
    "-p",
    type=click.STRING,
    required=False,
    help="The Python interpreter to use for the run environment. [env: UV_PYTHON=]",
)
@click.option(
    "--mode",
    type=click.Choice(["replace", "managed", "dry"]),
    default=lambda: os.environ.get("JUV_RUN_MODE", "replace"),
    hidden=True,
)
@click.argument(
    "jupyter_args", nargs=-1, type=click.UNPROCESSED
)  # Capture all args after --
def run(  # noqa: PLR0913
    *,
    file: str,
    jupyter: str,
    with_args: tuple[str, ...],
    python: str | None,
    jupyter_args: tuple[str, ...],
    mode: str,
) -> None:
    """Launch a notebook or script in a Jupyter front end."""
    from ._run import run

    run(
        path=Path(file),
        jupyter=jupyter,
        python=python,
        with_args=with_args,
        jupyter_args=jupyter_args,
        mode=mode,
    )


@cli.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True), required=True)
@click.option(
    "--check",
    is_flag=True,
    help="Check if the notebooks are cleared.",
)
def clear(*, files: list[str], check: bool) -> None:  # noqa: C901
    """Clear notebook cell outputs.

    Supports multiple files and glob patterns (e.g., *.ipynb, notebooks/*.ipynb)
    """
    from ._clear import clear, is_cleared

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

    if check:
        any_cleared = False
        for path in paths:
            if not is_cleared(path):
                rich.print(path.resolve().absolute(), file=sys.stderr)
                any_cleared = True

        if any_cleared:
            rich.print(
                "Some notebooks are not cleared. "
                "Use `[green b]juv clear[/green b]` to fix.",
                file=sys.stderr,
            )
            sys.exit(1)

        rich.print("All notebooks are cleared", file=sys.stderr)
        return

    if len(paths) == 1:
        clear(paths[0])
        path = os.path.relpath(paths[0].resolve(), Path.cwd())
        rich.print(f"Cleared output from `[cyan]{path}[/cyan]`", file=sys.stderr)
        return

    for path in paths:
        clear(path)
        rich.print(path.resolve().absolute(), file=sys.stderr)

    rich.print(f"Cleared output from {len(paths)} notebooks", file=sys.stderr)


@cli.command()
@click.argument("notebook", type=click.Path(exists=True), required=True)
@click.option(
    "--editor",
    type=click.STRING,
    required=False,
    help="The editor to use. [env: EDITOR=]",
)
def edit(*, notebook: str, editor: str | None) -> None:
    """Quick edit a notebook as markdown."""
    from ._edit import EditorAbortedError, edit

    if editor is None:
        editor = os.environ.get("EDITOR")

    if editor is None:
        msg = (
            "No editor specified. Please set the EDITOR environment variable "
            "or use the --editor option."
        )
        rich.print(f"[bold red]error[/bold red]: {msg}", file=sys.stderr)
        return

    path = Path(notebook)
    if path.suffix != ".ipynb":
        rich.print(
            f"[bold red]error[/bold red]: `[cyan]{path}[/cyan]` is not a notebook",
            file=sys.stderr,
        )
        return

    try:
        edit(path=path, editor=editor)
        rich.print(f"Edited `[cyan]{notebook}[/cyan]`", file=sys.stderr)
    except EditorAbortedError as e:
        rich.print(f"[bold red]error[/bold red]: {e}", file=sys.stderr)


def upgrade_legacy_jupyter_command(args: list[str]) -> None:
    """Check legacy command usage and upgrade to 'run' with deprecation notice."""
    if len(args) >= 2:  # noqa: PLR2004
        command = args[1]
        if command.startswith(("lab", "notebook", "nbclassic")):
            rich.print(
                f"[bold]warning[/bold]: The command '{command}' is deprecated. "
                f"Please use 'run' with `--jupyter={command}` "
                f"or set JUV_JUPYTER={command}",
                file=sys.stderr,
            )
            os.environ["JUV_JUPYTER"] = command
            args[1] = "run"


@cli.command("exec")
@click.argument("notebook", type=click.Path(exists=True), required=True)
@click.option(
    "--python",
    "-p",
    type=click.STRING,
    required=False,
    help="The Python interpreter to use for the exec environment. [env: UV_PYTHON=]",
)
@click.option(
    "--with",
    "with_args",
    type=click.STRING,
    multiple=True,
    help="Run with the given packages installed.",
)
@click.option("--quiet", is_flag=True)
def exec_(
    *, notebook: str, python: str | None, with_args: tuple[str, ...], quiet: bool
) -> None:
    """Execute a notebook as a script."""
    from ._exec import exec_

    exec_(path=Path(notebook), python=python, with_args=with_args, quiet=quiet)


@cli.command()
@click.argument("notebook", type=click.Path(exists=True), required=True)
@click.option("--script", is_flag=True)
@click.option(
    "--pager",
    type=click.STRING,
    help="The pager to use.",
    default=lambda: os.environ.get("JUV_PAGER"),
    hidden=True,
)
def cat(*, notebook: str, script: bool, pager: str | None) -> None:
    """Print notebook contents to stdout."""
    from ._cat import cat

    path = Path(notebook)
    if path.suffix != ".ipynb":
        rich.print(
            f"[bold red]error[/bold red]: `[cyan]{path}[/cyan]` is not a notebook",
            file=sys.stderr,
        )
        sys.exit(1)

    cat(path=path, script=script, pager=pager)


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--time",
    help=(
        "Accepts both RFC 3339 timestamps (e.g., 2006-12-02T02:07:43Z) and local dates "
        "in the same format (e.g., 2006-12-02) in your system's configured time zone."
    ),
)
@click.option("--rev", help="A Git revision to stamp the file with.")
@click.option("--latest", is_flag=True, help="Use the latest Git revision.")
@click.option("--clear", is_flag=True, help="Clear the `exclude-newer` field.")
def stamp(
    *,
    file: str,
    time: str | None,
    rev: str | None,
    latest: bool,
    clear: bool,
) -> None:
    """Stamp a notebook or script with a reproducible timestamp."""
    from ._stamp import CreateAction, DeleteAction, UpdateAction, stamp

    console = Console(file=sys.stderr, highlight=False)
    path = Path(file)

    # time, rev, latest, and clear are mutually exclusive
    if sum([bool(time), bool(rev), latest, clear]) > 1:
        console.print(
            "[bold red]Error:[/bold red] "
            "Only one of --time, --rev, --latest, or --clear may be specified",
        )
        sys.exit(1)

    try:
        action = stamp(path=path, time=time, rev=rev, latest=latest, clear=clear)
    except ValueError as e:
        console.print(f"[bold red]error[/bold red]: {e.args[0]}")
        sys.exit(1)

    path = os.path.relpath(path.resolve(), Path.cwd())

    if isinstance(action, DeleteAction):
        if action.previous is None:
            # there was no previosu timestamp, so ok but no-op
            console.print(f"No timestamp found in `[cyan]{path}[/cyan]`")
        else:
            console.print(
                f"Removed [green]{action.previous}[/green] from `[cyan]{path}[/cyan]`",
            )
    elif isinstance(action, CreateAction):
        console.print(
            f"Stamped `[cyan]{path}[/cyan]` with [green]{action.value}[/green]",
        )
    elif isinstance(action, UpdateAction):
        console.print(
            f"Updated `[cyan]{path}[/cyan]` with [green]{action.value}[/green]",
        )


def main() -> None:
    """Run the CLI."""
    upgrade_legacy_jupyter_command(sys.argv)
    cli()
