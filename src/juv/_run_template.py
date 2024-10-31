from __future__ import annotations

import pathlib
import typing
from dataclasses import dataclass

RuntimeName = typing.Literal["notebook", "lab", "nbclassic"]


def is_notebook_kind(kind: str) -> typing.TypeGuard[RuntimeName]:
    return kind in {"notebook", "lab", "nbclassic"}


@dataclass
class Runtime:
    name: RuntimeName
    version: str | None = None

    @classmethod
    def try_from_specifier(cls, value: str) -> Runtime:
        if "@" in value:
            parts = value.split("@")
        elif "==" in value:
            parts = value.split("==")
        else:
            parts = [value]

        if len(parts) == 2 and is_notebook_kind(parts[0]):  # noqa: PLR2004
            return Runtime(parts[0], parts[1])

        if len(parts) == 1 and is_notebook_kind(parts[0]):
            return Runtime(parts[0])

        msg = f"Invalid runtime specifier: {value}"
        raise ValueError(msg)

    def script_template(self) -> str:
        if self.name == "lab":
            return LAB
        if self.name == "notebook":
            if self.version and self.version.startswith("6"):
                return NOTEBOOK_6
            return NOTEBOOK
        if self.name == "nbclassic":
            return NBCLASSIC
        msg = f"Invalid self: {self.name}"
        raise ValueError(msg)

    def as_with_arg(self) -> str:
        # lab is actually jupyterlab
        with_ = "jupyterlab" if self.name == "lab" else self.name

        # append version if present
        if self.version:
            with_ += f"=={self.version}"

        # notebook v6 requires setuptools
        if with_ == "notebook" and self.version and self.version.startswith("6"):
            with_ += ",setuptools"

        return with_


LAB = """
{meta}
import sys from jupyterlab.labapp import main

sys.argv = ["jupyter-lab", "{notebook}", *{args}]
main()
"""

NOTEBOOK = """
{meta}
import sys
from notebook.app import main

sys.argv = ["jupyter-notebook", "{notebook}", *{args}]
main()
"""

NOTEBOOK_6 = """
{meta}
import sys
from notebook.notebookapp import main

sys.argv = ["jupyter-notebook", "{notebook}", *{args}]
main()
"""

NBCLASSIC = """
{meta}
import sys
from nbclassic.notebookapp import main

sys.argv = ["jupyter-nbclassic", "{notebook}", *{args}]
main()
"""


def prepare_run_script_and_uv_run_args(  # noqa: PLR0913
    *,
    runtime: Runtime,
    meta: str,
    target: pathlib.Path,
    python: str | None,
    with_args: typing.Sequence[str],
    jupyter_args: typing.Sequence[str],
    no_project: bool,
) -> tuple[str, list[str]]:
    script = runtime.script_template().format(
        meta=meta, notebook=target, args=jupyter_args
    )
    args = [
        "run",
        *(["--no-project"] if no_project else []),
        *([f"--python={python}"] if python else []),
        f"--with={runtime.as_with_arg()}",
        *(["--with=" + ",".join(with_args)] if with_args else []),
        "-",
    ]
    return script, args
