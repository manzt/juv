from __future__ import annotations

import os
import subprocess
import sys

from uv import find_uv_bin


def uv(args: list[str], *, check: bool) -> subprocess.CompletedProcess:
    """Invoke a uv subprocess and return the result.

    Parameters
    ----------
    args : list[str]
        The arguments to pass to the subprocess.

    check : bool
        Whether to raise an exception if the subprocess returns a non-zero exit code.

    Returns
    -------
    subprocess.CompletedProcess
        The result of the subprocess.

    """
    uv = os.fsdecode(find_uv_bin())
    return subprocess.run([uv, *args], capture_output=True, check=check, env=os.environ)  # noqa: S603
