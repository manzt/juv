from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from uv import find_uv_bin

IS_WINDOWS = sys.platform.startswith("win")


def run(script: str, args: list[str], lockfile_contents: str | None) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w+",
        delete=True,
        suffix=".py",
        encoding="utf-8",
    ) as f:
        lockfile = Path(f"{f.name}.lock")
        f.write(script)
        f.flush()

        if lockfile_contents:
            lockfile.write_text(lockfile_contents)

        if not IS_WINDOWS:
            process = subprocess.Popen(  # noqa: S603
                [os.fsdecode(find_uv_bin()), *args, f.name],
                stdout=sys.stdout,
                stderr=sys.stderr,
                preexec_fn=os.setsid,  # noqa: PLW1509
            )
        else:
            process = subprocess.Popen(  # noqa: S603
                [os.fsdecode(find_uv_bin()), *args, f.name],
                stdout=sys.stdout,
                stderr=sys.stderr,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )

        try:
            process.wait()
        except KeyboardInterrupt:
            if not IS_WINDOWS:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                os.kill(process.pid, signal.SIGTERM)
        finally:
            lockfile.unlink(missing_ok=True)
            process.wait()
