import contextlib  # noqa: D100, INP001
import json
import os
import signal
import sys
import tempfile
from pathlib import Path

from platformdirs import user_data_dir


# Custom TemporaryDirectory for Python < 3.10
# TODO: Use `ignore_cleanup_errors=True` in Python 3.10+
class TemporaryDirectoryIgnoreErrors(tempfile.TemporaryDirectory):  # noqa: D101
    def cleanup(self) -> None:  # noqa: D102
        with contextlib.suppress(Exception):
            super().cleanup()  # Ignore cleanup errors


TEMP_DIR: "TemporaryDirectoryIgnoreErrors | None" = None


def setup_jupyter_data_dirs() -> "tuple[Path, list[Path]]":  # noqa: D103
    global TEMP_DIR  # noqa: PLW0603

    juv_data_dir = Path(user_data_dir("juv"))
    juv_data_dir.mkdir(parents=True, exist_ok=True)

    TEMP_DIR = TemporaryDirectoryIgnoreErrors(dir=juv_data_dir)
    merged_data_dir = Path(TEMP_DIR.name)

    def handle_termination(signum, frame) -> None:  # noqa: ANN001, ARG001
        if TEMP_DIR:
            TEMP_DIR.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_termination)
    signal.signal(signal.SIGINT, handle_termination)

    config_paths: "list[Path]" = []  # noqa: UP037
    root_data_dir = Path(sys.prefix) / "share" / "jupyter"
    jupyter_paths = [root_data_dir]
    for path in map(Path, sys.path):
        if path.name != "site-packages":
            continue
        venv_path = path.parent.parent.parent
        config_paths.append(venv_path / "etc" / "jupyter")
        data_dir = venv_path / "share" / "jupyter"
        if not data_dir.exists() or str(data_dir) == str(root_data_dir):
            continue

        jupyter_paths.append(data_dir)

    for path in reversed(jupyter_paths):
        for item in path.rglob("*"):
            if item.is_file():
                dest = merged_data_dir / item.relative_to(path)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with contextlib.suppress(FileExistsError):
                    os.link(item, dest)

    return merged_data_dir, config_paths


def write_notebook_lockfile_contents_and_delete(  # noqa: D103
    notebook: str,
    lockfile: "str | None",
) -> None:
    if not lockfile:
        return

    notebook_path = Path(notebook)
    lockfile_path = Path(lockfile)

    with notebook_path.open(encoding="utf-8") as f:
        nb = json.load(f)

    # Replace contents and rewrite notebook file before opening
    nb.setdefault("metadata", {})["uv.lock"] = lockfile_path.read_text("utf-8")

    with notebook_path.open(mode="w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
        f.write("\\n")

    # delete the lock file
    lockfile_path.unlink(missing_ok=True)


def setup(notebook: str, jupyter: str, run_mode: str) -> None:  # noqa: D103
    write_notebook_lockfile_contents_and_delete(
        notebook,
        os.environ.get("JUV_LOCKFILE_PATH"),
    )

    # relay notebook info to managed session
    if run_mode == "managed":
        import importlib.metadata

        version = importlib.metadata.version(jupyter)
        print(f"JUV_MANGED={jupyter},{version}", file=sys.stderr)  # noqa: T201

    # wire up juptyer dirs for this enviroment
    data_dir, config_paths = setup_jupyter_data_dirs()
    os.environ["JUPYTER_DATA_DIR"] = str(data_dir)
    os.environ["JUPYTER_CONFIG_PATH"] = os.pathsep.join(map(str, config_paths))

    # delete this temporary script
    with contextlib.suppress(PermissionError):
        # FIXME: On Windows, a running script cannot be unlinked
        # because it's locked by the process. Therefore, we can't
        # cleanup the file until after the Jupyter server exists
        # like on unix.
        Path(str(__file__)).unlink(missing_ok=True)
