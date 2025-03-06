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


def uv_piped(
    args: list[str],
    *,
    check: bool,
    env: dict | None = None,
    input: bytes | None = None,  # noqa: A002
) -> subprocess.CompletedProcess:
    """Invoke a uv subprocess and stream the output to the console.

    Parameters
    ----------
    args : list[str]
        The arguments to pass to the subprocess.

    check : bool
        Whether to raise an exception if the subprocess returns a non-zero exit code.

    env : dict | None
        The system enviroment to run the subprocess.

    input : bytes | None
        Contents to forwads as input to the subprocess.

    Returns
    -------
    subprocess.CompletedProcess
        The result of the subprocess.

    """
    uv = os.fsdecode(find_uv_bin())
    return subprocess.run(  # noqa: S603
        [uv, *args],
        check=check,
        env=env or os.environ,
        stdout=sys.stdout,
        stderr=sys.stderr,
        input=input,
    )
