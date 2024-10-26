import importlib.metadata
import json
import pathlib
import shutil
import typing
import zipfile

from ._version import __version__

SELF_DIR = pathlib.Path(__file__).parent


def data_files() -> typing.Generator[tuple[str, str]]:
    deno = shutil.which("deno")
    if deno:
        yield (
            "share/jupyter/kernels/deno/kernel.json",
            json.dumps(
                {
                    "argv": [
                        deno,
                        "jupyter",
                        "--kernel",
                        "--conn",
                        "{connection_file}",
                    ],
                    "display_name": "Deno",
                    "language": "typescript",
                }
            ),
        )


def get_juv_jupyter_wheel() -> pathlib.Path:
    name = "juv"
    version = __version__
    wheel = SELF_DIR / f"{name}-{version}-py3-none-any.whl"

    with zipfile.ZipFile(wheel, "w") as zf:
        record = []

        for target, file in [
            (f"{name}/__init__.py", "_cellmagic.py"),
            (f"{name}/_pep723.py", "_pep723.py"),
        ]:
            zf.writestr(target, (SELF_DIR / file).read_text())
            record.append(f"{target},,")

        for src, contents in data_files():
            zf.writestr(f"{name}-{version}.data/data/{src}", contents)
            record.append(f"{name}-{version}.data/data/{src},,")

        zf.writestr(
            f"{name}-{version}.dist-info/WHEEL",
            "\n".join(
                [  # noqa: FLY002
                    "Wheel-Version: 1.0",
                    "Generator: juv (1.0.0)",
                    "Root-Is-Purelib: true",
                    "Tag: py3-none-any",
                ]
            ),
        )
        zf.writestr(
            f"{name}-{version}.dist-info/METADATA",
            "\n".join(
                [
                    "Metadata-Version: 2.1",
                    f"Name: {name}",
                    f"Version: {version}",
                    "Summary: Installs some client utilties for juv",
                    "License: MIT",
                    f"Requires-Dist: uv=={importlib.metadata.version('uv')}",
                ]
            ),
        )
        record.extend(
            (
                f"{name}-{version}.dist-info/WHEEL,,",
                f"{name}-{version}.dist-info/METADATA,,",
                f"{name}-{version}.dist-info/RECORD,,",
            )
        )
        zf.writestr(f"{name}-{version}.dist-info/RECORD", "\n".join(record))

    return wheel
