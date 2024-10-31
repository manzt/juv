from __future__ import annotations
import json
import os
import signal
import subprocess
import sys

from uv import find_uv_bin

script_template = """
{meta}
import json
import jupyter_client
import rich

km = jupyter_client.KernelManager()
km.start_kernel()
kc = km.client()
kc.start_channels()

def execute_code(code: str):
    msg_id = kc.execute(code)

    while True:
        msg = kc.get_iopub_msg()
        msg_type = msg["header"]["msg_type"]

        if msg_type == "execute_result":
            return msg["content"]["data"]["text/plain"]
        elif msg_type == "stream":
            return msg["content"]["text"]
        elif msg_type == "error":
            return f"Error: {{msg["content"]["evalue"]}}"

try:
    for cell in {cells}:
        print("Output:", execute_code(cell))
finally:
    kc.stop_channels()
    km.shutdown_kernel(now=True)
"""

lab_template = """
{meta}
import sys
from jupyterlab.labapp import main

sys.argv = ["jupyter-lab", "{notebook}"]
main()
"""

notebook_template = """
{meta}
import sys
from notebook.app import main

sys.argv = ["jupyter-notebook", "{notebook}"]
main()
"""

notebook_6_template = """
{meta}
import sys
from notebook.notebookapp import main

sys.argv = ["jupyter-notebook", "{notebook}"]
main()
"""

nbclassic_template = """
{meta}
import sys
from nbclassic.notebookapp import main

sys.argv = ["jupyter-nbclassic", "{notebook}"]
main()
"""


def parse_kind(kind: str) -> tuple[str, str | None]:  # noqa: D103
    if "==" in kind:
        kind, version = kind.split("==", 1)
        return kind, version
    if "@" in kind:
        kind, version = kind.split("@", 1)
        return kind, version
    return kind, None


def main() -> None:  # noqa: D103
    notebook = sys.argv[1]
    kind, version = parse_kind(sys.argv[2])

    with open(notebook, encoding="utf-8") as f:  # noqa: PTH123
        nb = json.load(f)
        meta = "".join(nb["cells"][0]["source"])

    if kind == "lab":
        # alias for jupyterlab
        kind = "jupyterlab"

    args = [
        "run",
        "--no-project",
        f"--with={kind}=={version}" if version else f"--with={kind}",
    ]

    if kind == "jupyterlab":
        script = lab_template.format(meta=meta, notebook=notebook)
    elif kind == "nbclassic":
        script = nbclassic_template.format(meta=meta, notebook=notebook)
    elif kind == "notebook" and version is None:
        script = notebook_template.format(meta=meta, notebook=notebook)
    elif kind == "notebook":
        script = notebook_6_template.format(meta=meta, notebook=notebook)
        args += ["--with=setuptools"]
    else:
        msg = f"Unknown kind: {kind}"
        raise ValueError(msg)

    command = [os.fsdecode(find_uv_bin()), *args, "-"]

    process = subprocess.Popen(  # noqa: S603
        command,
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
