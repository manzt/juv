from __future__ import annotations

import os
import subprocess

from uv import find_uv_bin


def uv(args: list[str], check: bool) -> subprocess.CompletedProcess:
    """Invoke a uv subprocess and return the result."""
    uv = os.fsdecode(find_uv_bin())
    return subprocess.run(
        [uv, *args], capture_output=True, check=check
    )
