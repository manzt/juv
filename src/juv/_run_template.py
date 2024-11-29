from __future__ import annotations

import typing
from dataclasses import dataclass

if typing.TYPE_CHECKING:
    import pathlib

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
        if self.name == "notebook" and self.version:
            with_ += ",setuptools"

        return with_


SETUP_JUPYTER_DATA_DIR = """
import tempfile
import signal
from pathlib import Path
import os
import sys

from platformdirs import user_data_dir

juv_data_dir = Path(user_data_dir("juv"))
juv_data_dir.mkdir(parents=True, exist_ok=True)

temp_dir = tempfile.TemporaryDirectory(dir=juv_data_dir, ignore_cleanup_errors=True)
merged_dir = Path(temp_dir.name)

def handle_termination(signum, frame):
    temp_dir.cleanup()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_termination)
signal.signal(signal.SIGINT, handle_termination)

config_paths = []
root_data_dir = Path(sys.prefix) / "share" / "jupyter"
jupyter_paths = [root_data_dir]
for path in map(Path, sys.path):
    if not path.name == "site-packages":
        continue
    venv_path = path.parent.parent.parent
    config_paths.append(venv_path / "etc" / "jupyter")
    data_dir = venv_path / "share" / "jupyter"
    if not data_dir.exists() or str(data_dir) == str(root_data_dir):
        continue

    jupyter_paths.append(data_dir)


for path in reversed(jupyter_paths):
    for item in path.rglob('*'):
        if item.is_file():
            dest = merged_dir / item.relative_to(path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(item, dest)
            except FileExistsError:
                pass

os.environ["JUPYTER_DATA_DIR"] = str(merged_dir)
os.environ["JUPYTER_CONFIG_PATH"] = os.pathsep.join(map(str, config_paths))
"""

LAB = """
{meta}
import os
import sys

from jupyterlab.labapp import main

{SETUP_JUPYTER_DATA_DIR}

if {is_managed}:
    import importlib.metadata

    version = importlib.metadata.version("jupyterlab")
    print("JUV_MANGED=" + "jupyterlab" + "," + version, file=sys.stderr)

sys.argv = ["jupyter-lab", r"{notebook}", *{args}]
main()
"""

NOTEBOOK = """
{meta}
import os
import sys

from notebook.app import main

{SETUP_JUPYTER_DATA_DIR}

if {is_managed}:
    import importlib.metadata

    version = importlib.metadata.version("notebook")
    print("JUV_MANGED=" + "notebook" + "," + version, file=sys.stderr)

sys.argv = ["jupyter-notebook", r"{notebook}", *{args}]
main()
"""

NOTEBOOK_6 = """
{meta}
import os
import sys

from notebook.notebookapp import main

{SETUP_JUPYTER_DATA_DIR}

if {is_managed}:
    import importlib.metadata

    version = importlib.metadata.version("notebook")
    print("JUV_MANGED=" + "notebook" + "," + version, file=sys.stderr)

sys.argv = ["jupyter-notebook", r"{notebook}", *{args}]
main()
"""

NBCLASSIC = """
{meta}
import os
import sys

from nbclassic.notebookapp import main

{SETUP_JUPYTER_DATA_DIR}

if {is_managed}:
    import importlib.metadata

    version = importlib.metadata.version("nbclassic")
    print("JUV_MANGED=" + "nbclassic" + "," + version, file=sys.stderr)

os.environ["JUPYTER_DATA_DIR"] = str(merged_dir)
sys.argv = ["jupyter-nbclassic", r"{notebook}", *{args}]
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
    mode: str,
) -> tuple[str, list[str]]:
    script = runtime.script_template().format(
        meta=meta,
        notebook=target,
        args=jupyter_args,
        SETUP_JUPYTER_DATA_DIR=SETUP_JUPYTER_DATA_DIR,
        is_managed=mode == "managed",
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
