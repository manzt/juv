from __future__ import annotations

import os
import signal
import subprocess
import sys

from uv import find_uv_bin


def run(script: str, args: list[str]) -> None:
    process = subprocess.Popen(  # noqa: S603
        [os.fsdecode(find_uv_bin()), *args],
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
