from __future__ import annotations

import atexit
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from uv import find_uv_bin

IS_WINDOWS = sys.platform.startswith("win")


def run(script: str, args: list[str], lockfile_contents: str | None, dir: Path) -> None:  # noqa: A002
    with tempfile.NamedTemporaryFile(
        mode="w+",
        delete=False,
        suffix=".py",
        dir=dir,
        prefix="juv.tmp.",
        encoding="utf-8",
    ) as f:
        script_path = Path(f.name)
        atexit.register(lambda: script_path.unlink(missing_ok=True))

        lockfile = Path(f"{f.name}.lock")
        f.write(script)
        f.flush()

        env = os.environ.copy()

        if lockfile_contents:
            # Write the contents so UV picks it up
            lockfile.write_text(lockfile_contents)
            # Forward path to underlying process.
            # We rewrite the lockfile entry (if necessary) within that process.
            env["JUV_LOCKFILE_PATH"] = str(lockfile)

        if IS_WINDOWS:
            process = subprocess.Popen(  # noqa: S603
                [os.fsdecode(find_uv_bin()), *args, f.name],
                stdout=sys.stdout,
                stderr=sys.stderr,
                # Required so the subprocess is attached to our console;
                # needed for CTRL_BREAK_EVENT to propagate to the process group
                stdin=sys.stdin,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                env=env,
            )
        else:
            process = subprocess.Popen(  # noqa: S603
                [os.fsdecode(find_uv_bin()), *args, f.name],
                stdout=sys.stdout,
                stderr=sys.stderr,
                preexec_fn=os.setsid,  # noqa: PLW1509
                env=env,
            )

        try:
            process.wait()
        except KeyboardInterrupt:
            if IS_WINDOWS:
                os.kill(process.pid, signal.SIGTERM)
            else:
                # Send CTRL_BREAK_EVENT to the process group on Windows
                process.send_signal(signal.CTRL_BREAK_EVENT)
        finally:
            lockfile.unlink(missing_ok=True)
            process.wait()
