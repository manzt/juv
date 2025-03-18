from __future__ import annotations

import os
import tempfile
import typing
from pathlib import Path

import jupytext
import rich
from rich.console import Console

from juv._uv import uv

from ._nbutils import code_cell, write_ipynb
from ._pep723 import includes_inline_metadata
from ._utils import find

if typing.TYPE_CHECKING:
    import pathlib


def sync(
    path: pathlib.Path,
    *,
    python: str | None,
    frozen: bool = False,
    env_path: pathlib.Path,
) -> str:
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(env_path)

    if path.suffix == ".py":
        # just defer to uv behavior
        result = uv(
            [
                "sync",
                *(["--python", python] if python else []),
                "--active",
                "--script",
                str(path),
            ],
            check=True,
            env=env,
        )
        return result.stderr.decode("utf8")

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

        result = uv(
            [
                "sync",
                *(["--python", python] if python else []),
                "--active",
                "--script",
                f.name,
            ],
            env=env,
            check=True,
        )

        if not frozen and lockfile.exists():
            notebook.metadata["uv.lock"] = lockfile.read_text(encoding="utf-8")
            write_ipynb(notebook, path)
            lockfile.unlink(missing_ok=True)

        return result.stderr.decode("utf8")


def venv(
    *,
    source: pathlib.Path,
    python: str | None,
    path: pathlib.Path,
    no_kernel: bool,
) -> None:
    console = Console()
    rel_path = os.path.relpath(path.resolve(), Path.cwd())
    if path.exists():
        rich.print(f"Using notebook environment at: `[cyan]{rel_path}[/cyan]`")
    else:
        rich.print(f"Creating notebook environment at: `[cyan]{rel_path}[/cyan]`")

    uv_output = sync(source, python=python, env_path=path)
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(path)
    if not no_kernel:
        uv(["pip", "install", "ipykernel"], env=env, check=True)

    for line in uv_output.split("\n"):
        if line.startswith((" +", " -", " ~")):
            prefix, suffix = line.split("==")
            symbol, name = prefix.strip().split(" ")
            color = {"+": "green", "-": "red", "~": "yellow"}[symbol]
            if name in IGNORE_PACKAGES:
                continue
            console.print(
                f" [{color}]{symbol}[/{color}] [bold]{name}[/bold][dim]=={suffix}[/dim]",  # noqa: E501
                highlight=False,
            )


# These packages are dependencies of `ipykernel` so they add a lot of noise to output.
# We filter them out when reporting differences in the environment.
IGNORE_PACKAGES = {
    "appnope",
    "asttokens",
    "comm",
    "debugpy",
    "decorator",
    "executing",
    "ipykernel",
    "ipython",
    "ipython-pygments-lexers",
    "jedi",
    "jupyter-client",
    "jupyter-core",
    "matplotlib-inline",
    "nest-asyncio",
    "packaging",
    "parso",
    "pexpect",
    "platformdirs",
    "prompt-toolkit",
    "psutil",
    "ptyprocess",
    "pure-eval",
    "pygments",
    "python-dateutil",
    "pyzmq",
    "six",
    "stack-data",
    "tornado",
    "traitlets",
    "wcwidth",
}
