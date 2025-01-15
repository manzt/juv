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


UPDATE_LOCKFILE = """
import json
import os

def update_uv_lock(notebook_path: str):
    lockfile_path = os.environ.get("JUV_LOCKFILE_PATH")

    if not lockfile_path:
        return

    with open(lockfile_path, "r", encoding="utf-8") as lockfile:
        lock_contents = lockfile.read()

    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Replace contents and rewrite notebook file before opening
    nb.setdefault("metadata", {{}})["uv.lock"] = lock_contents
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
        f.write("\\n")

update_uv_lock(r"{notebook}")
"""

DELETE_RUN_SCRIPT_AND_LOCKFILE = """
import os
from pathlib import Path

def delete_run_script_and_lockfile():
    Path(str(__file__)).unlink(missing_ok=True)
    lockfile_path = os.environ.get("JUV_LOCKFILE_PATH")
    if not lockfile_path:
        return
    Path(lockfile_path).unlink(missing_ok=True)

delete_run_script_and_lockfile()
"""


SETUP_JUPYTER_DATA_DIR = """
import tempfile
import signal
from pathlib import Path
import os
import sys

from platformdirs import user_data_dir

juv_data_dir = Path(user_data_dir("juv"))
juv_data_dir.mkdir(parents=True, exist_ok=True)

# Custom TemporaryDirectory for Python < 3.10
# TODO: Use `ignore_cleanup_errors=True` in Python 3.10+
class TemporaryDirectoryIgnoreErrors(tempfile.TemporaryDirectory):
    def cleanup(self):
        try:
            super().cleanup()
        except Exception:
            pass  # Ignore cleanup errors

temp_dir = TemporaryDirectoryIgnoreErrors(dir=juv_data_dir)
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

{UPDATE_LOCKFILE}
{DELETE_RUN_SCRIPT_AND_LOCKFILE}
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

{UPDATE_LOCKFILE}
{DELETE_RUN_SCRIPT_AND_LOCKFILE}
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

{UPDATE_LOCKFILE}
{DELETE_RUN_SCRIPT_AND_LOCKFILE}
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

{UPDATE_LOCKFILE}
{DELETE_RUN_SCRIPT_AND_LOCKFILE}
{SETUP_JUPYTER_DATA_DIR}

if {is_managed}:
    import importlib.metadata

    version = importlib.metadata.version("nbclassic")
    print("JUV_MANGED=" + "nbclassic" + "," + version, file=sys.stderr)

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
        UPDATE_LOCKFILE=UPDATE_LOCKFILE.format(notebook=target),
        DELETE_RUN_SCRIPT_AND_LOCKFILE=DELETE_RUN_SCRIPT_AND_LOCKFILE,
        is_managed=mode == "managed",
    )
    args = [
        "run",
        *(["--no-project"] if no_project else []),
        *([f"--python={python}"] if python else []),
        f"--with={runtime.as_with_arg()}",
        *(["--with=" + ",".join(with_args)] if with_args else []),
        "--script",
    ]
    return script, args
