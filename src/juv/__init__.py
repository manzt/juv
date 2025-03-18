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
    type=click.STRING,
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
@click.option(
    "--pin", is_flag=True, help="Resolve package specifiers to exact versions and pin."
)
@click.option(
    "--exclude-newer",
    type=click.STRING,
    help=(
        "Limit candidate packages to those that were uploaded prior to the given date "
        "[env: UV_EXCLUDE_NEWER=]"
    ),
)
@click.option(
    "--index",
    type=click.STRING,
    help="The URLs to use when resolving dependencies, in addition to the default "
    "index [env: UV_INDEX=]",
)
@click.option(
    "--default-index",
    type=click.STRING,
    help="The URL of the default package index (by default: <https://pypi.org/simple>) "
    "[env: UV_DEFAULT_INDEX=]",
)
@click.argument("packages", nargs=-1, required=False)
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
    pin: bool,
    exclude_newer: str | None,
    index: str | None,
    default_index: str | None,
) -> None:
    """Add dependencies to a notebook or script."""
    from ._add import add

    if requirements is None and len(packages) == 0:
        msg = "Must provide one of --requirements or PACKAGES."
        raise click.UsageError(msg)

    try:
        add(
            path=Path(file),
            packages=packages,
            requirements=requirements,
            extras=extras,
            editable=editable,
            tag=tag,
            branch=branch,
            rev=rev,
            pin=pin,
            exclude_newer=exclude_newer,
            index=index,
            default_index=default_index,
        )
        path = os.path.relpath(Path(file).resolve(), Path.cwd())
        rich.print(f"Updated `[cyan]{path}[/cyan]`")
    except RuntimeError as e:
        rich.print(e, file=sys.stderr)
        sys.exit(1)


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
    "--timestamp",
    help="An RFC 3339 timestamp (e.g., 2006-12-02T02:07:43Z).",
)
@click.option(
    "--date",
    help=(
        "A local ISO 8601 date (e.g., 2006-12-02). "
        "Resolves to midnight system's time zone."
    ),
)
@click.option("--rev", help="A Git revision to stamp the file with.")
@click.option("--latest", is_flag=True, help="Use the latest Git revision.")
@click.option("--clear", is_flag=True, help="Clear the `exclude-newer` field.")
def stamp(  # noqa: PLR0913
    *,
    file: str,
    timestamp: str | None,
    date: str | None,
    rev: str | None,
    latest: bool,
    clear: bool,
) -> None:
    """Stamp a notebook or script with a reproducible timestamp."""
    if sys.version_info < (3, 9):
        rich.print(
            "[bold red]error[/bold red] "
            "Python 3.9 or latest is required for `juv stamp`",
        )
        sys.exit(1)

    from ._stamp import CreateAction, DeleteAction, UpdateAction, stamp

    console = Console(file=sys.stderr, highlight=False)
    path = Path(file)

    # time, rev, latest, and clear are mutually exclusive
    if sum([bool(timestamp), bool(rev), bool(date), latest, clear]) > 1:
        console.print(
            "[bold red]Error:[/bold red] "
            "Only one of --timestamp, --date, --rev, --latest, or --clear may be used",
        )
        sys.exit(1)

    try:
        action = stamp(
            path=path,
            timestamp=timestamp,
            rev=rev,
            latest=latest,
            clear=clear,
            date=date,
        )
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


@cli.command()
@click.argument("file", type=click.Path(exists=True), required=True)
@click.argument("packages", nargs=-1, required=True)
def remove(
    *,
    file: str,
    packages: tuple[str, ...],
) -> None:
    """Remove dependencies from a notebook."""
    from ._remove import remove

    try:
        remove(
            path=Path(file),
            packages=packages,
        )
        path = os.path.relpath(Path(file).resolve(), Path.cwd())
        rich.print(f"Updated `[cyan]{path}[/cyan]`")
    except RuntimeError as e:
        rich.print(e, file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.argument("file", type=click.Path(exists=True), required=True)
@click.option("--clear", is_flag=True, help="Clear the lockfile contents.")
def lock(
    *,
    file: str,
    clear: bool,
) -> None:
    """Update the notebooks's lockfile."""
    from ._lock import lock

    try:
        lock(path=Path(file), clear=clear)
        path = os.path.relpath(Path(file).resolve(), Path.cwd())
        if clear:
            rich.print(f"Cleared lockfile `[cyan]{path}[/cyan]`")
        else:
            rich.print(f"Locked `[cyan]{path}[/cyan]`")
    except RuntimeError as e:
        rich.print(e, file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.argument("file", type=click.Path(exists=True), required=True)
def tree(
    *,
    file: str,
) -> None:
    """Display the notebook's dependency tree."""
    from ._tree import tree

    tree(path=Path(file))


@cli.command()
@click.argument("file", type=click.Path(exists=True), required=True)
def export(
    *,
    file: str,
) -> None:
    """Export the notebook's lockfile to an alternate format."""
    from ._export import export

    export(path=Path(file))


@cli.command()
@click.option(
    "--from",
    "from_",
    type=click.Path(exists=True),
    required=True,
    help="The notebook or script from which to derive the virtual environment.",
)
@click.option(
    "--python",
    "-p",
    type=click.STRING,
    required=False,
    help="The Python interpreter to use to determine the minimum supported Python version. [env: UV_PYTHON=]",  # noqa: E501
)
@click.option(
    "--no-kernel", is_flag=True, help="Exclude `ipykernel` from the enviroment."
)
@click.argument(
    "path",
    required=False,
)
def venv(
    *,
    from_: str,
    python: str | None,
    no_kernel: bool,
    path: str | None,
) -> None:
    """Create a virtual enviroment from a notebook."""
    from ._venv import venv

    try:
        venv(
            source=Path(from_),
            python=python,
            path=Path.cwd() / ".venv" if path is None else Path(path),
            no_kernel=no_kernel,
        )
    except RuntimeError as e:
        rich.print(e, file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.option(
    "--target",
    type=click.Path(exists=False),
    required=False,
    help="Path to virtual environment to sync. Falls back to `.venv` in current directory.",  # noqa: E501
)
@click.option(
    "--active",
    is_flag=True,
    help="Sync dependencies to the active virtual environment. Overrides --target.",
)
@click.option(
    "--python",
    "-p",
    type=click.STRING,
    required=False,
    help="The Python interpreter to use to determine the minimum supported Python version. [env: UV_PYTHON=]",  # noqa: E501
)
@click.option(
    "--no-kernel", is_flag=True, help="Exclude `ipykernel` from the environment."
)
@click.argument(
    "path",
    required=True,
)
def sync(
    *,
    target: str | None,
    active: bool,
    python: str | None,
    no_kernel: bool,
    path: str,
) -> None:
    """Sync a virtual enviroment for a notebook."""
    from ._venv import venv

    if target is not None and active:
        msg = "Provide either --target or --active, but not both."
        raise click.UsageError(msg)

    if active:
        venv_target = Path(os.environ.get("VIRTUAL_ENV", Path.cwd() / ".venv"))
    elif target:
        venv_target = Path(target)
    else:
        venv_target = Path.cwd() / ".venv"

    try:
        venv(
            source=Path(path),
            python=python,
            path=venv_target,
            no_kernel=no_kernel,
        )
    except RuntimeError as e:
        rich.print(e, file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Run the CLI."""
    upgrade_legacy_jupyter_command(sys.argv)
    cli()
