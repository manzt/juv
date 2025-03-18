from __future__ import annotations

import os
import subprocess

from uv import find_uv_bin


def uv(
    args: list[str],
    *,
    check: bool,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Invoke a uv subprocess and return the result.

    Parameters
    ----------
    args : list[str]
        The arguments to pass to the subprocess.

    check : bool
        Whether to raise an exception if the subprocess returns a non-zero exit code.

    env : dict | None
        The system enviroment to run the subprocess.

    Returns
    -------
    subprocess.CompletedProcess
        The result of the subprocess.

    """
    uv = os.fsdecode(find_uv_bin())
    return subprocess.run(  # noqa: S603
        [uv, *args], capture_output=True, check=check, env=env or os.environ
    )
