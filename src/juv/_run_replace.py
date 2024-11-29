from __future__ import annotations

import os
import platform
import signal
import subprocess
import sys

from uv import find_uv_bin

IS_WINDOWS = platform.system()

def run(script: str, args: list[str]) -> None:
    if not IS_WINDOWS:
        process = subprocess.Popen(  # noqa: S603
            [os.fsdecode(find_uv_bin()), *args],
            stdin=subprocess.PIPE,
            stdout=sys.stdout,
            stderr=sys.stderr,
            preexec_fn=os.setsid,  # noqa: PLW1509
        )
    else:
        process = subprocess.Popen(  # noqa: S603
            [os.fsdecode(find_uv_bin()), *args],
            stdin=subprocess.PIPE,
            stdout=sys.stdout,
            stderr=sys.stderr,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        ) 

    assert process.stdin is not None  # noqa: S101
    process.stdin.write(script.encode())
    process.stdin.flush()
    process.stdin.close()

    try:
        process.wait()
    except KeyboardInterrupt:
        if not IS_WINDOWS:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        else:
            os.kill(process.pid, signal.SIGTERM)
    finally:
        process.wait()
