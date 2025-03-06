from __future__ import annotations

import os
import typing

from juv._uv import uv_piped

from ._export import export_to_string

if typing.TYPE_CHECKING:
    import pathlib


def venv(
    *,
    source: pathlib.Path,
    python: str | None,
    path: pathlib.Path | None,
    no_kernel: bool,
) -> None:
    uv_piped(
        [
            "venv",
            *(["--python", python] if python else []),
            *([str(path)] if path else []),
        ],
        check=True,
    )

    locked_requirements = export_to_string(source)
    if not no_kernel:
        locked_requirements += "ipykernel\n"

    env = os.environ.copy()
    if path:
        env["VIRTUAL_ENV"] = str(path)

    uv_piped(
        ["pip", "install", "-r", "-"],
        env=env,
        input=locked_requirements.encode("utf-8"),
        check=True,
    )
