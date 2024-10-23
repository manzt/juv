import subprocess

from uv import find_uv_bin
import os


def uv(args: list[str], check: bool) -> subprocess.CompletedProcess:
    """Invoke a uv subprocess and return the stdout."""

    uv = os.fsdecode(find_uv_bin())
    result = subprocess.run([uv] + args, stdout=subprocess.PIPE, check=check)
    return result
