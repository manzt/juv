from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import sys
import typing

lab_template = """
{meta}
import sys from jupyterlab.labapp import main

sys.argv = ["jupyter-lab", "{notebook}", *{args}]
main()
"""

notebook_template = """
{meta}
import sys
from notebook.app import main

sys.argv = ["jupyter-notebook", "{notebook}", *{args}]
main()
"""

notebook_6_template = """
{meta}
import sys
from notebook.notebookapp import main

sys.argv = ["jupyter-notebook", "{notebook}", *{args}]
main()
"""

nbclassic_template = """
{meta}
import sys
from nbclassic.notebookapp import main

sys.argv = ["jupyter-nbclassic", "{notebook}", *{args}]
main()
"""


def get_args_and_template(
    kind: typing.Literal["jupyterlab", "notebook", "nbclassic"],
    version: str | None,
    jupyter_args: list[str],
    meta: str,
    notebook: pathlib.Path,
) -> tuple[str, list[str]]:
    args = [
        "run",
        "--no-project",
        f"--with={kind}=={version}" if version else f"--with={kind}",
    ]

    template = {
        "jupyterlab": lab_template,
        "notebook": notebook_template,
        "nbclassic": nbclassic_template,
    }[kind]

    if kind == "notebook" and version and version.startswith("6"):
        template = notebook_6_template
        args += ["--with=setuptools"]

    script = template.format(meta=meta, notebook=notebook, args=jupyter_args)

    return script, [*args, "-"]


def main():
    import sys

    from uv import find_uv_bin

    script, args = get_args_and_template(
        kind=sys.argv[1],
        notebook=pathlib.Path(sys.argv[2]),
        jupyter_args=sys.argv[3:],
        version="",
        meta="",
    )

    process = subprocess.Popen(  # noqa: S603
        [find_uv_bin(), *args],
        stdin=subprocess.PIPE,
        stdout=sys.stdout,
        stderr=sys.stderr,
        preexec_fn=os.setsid,  # noqa: PLW1509
    )

    assert process.stdin is not None  # noqa: S101
    process.stdin.write(script.encode())
    process.stdin.flush()
    process.stdin.close()

    try:
        process.wait()
    except KeyboardInterrupt:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    finally:
        process.wait()


if __name__ == "__main__":
    main()
