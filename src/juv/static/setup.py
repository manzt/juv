import contextlib  # noqa: D100, INP001
import json
import os
import sys
from pathlib import Path


def find_jupyter_paths() -> "tuple[list[Path], list[Path]]":
    """Locate Jupyter directories within the current virtual environment.

    Ref: https://docs.jupyter.org/en/stable/use/jupyter-directories.html
    """
    jupyter_paths = [Path(sys.prefix) / "share" / "jupyter"]
    config_paths: "list[Path]" = []  # noqa: UP037
    for path in map(Path, sys.path):
        if path.name != "site-packages":
            continue

        if os.name == "nt":  # noqa: SIM108
            # Windows: <venv>/Lib/site-packages → go up 2 levels
            venv = path.parent.parent
        else:
            # Unix: <venv>/lib/pythonX.Y/site-packages → go up 3 levels
            venv = path.parent.parent.parent

        jupyter_path = (venv / "share" / "jupyter").resolve()
        if jupyter_path.exists() and jupyter_path not in jupyter_paths:
            jupyter_paths.append(jupyter_path)

        config_path = (venv / "etc" / "jupyter").resolve()
        if config_path.exists() and config_path not in config_paths:
            config_paths.append(config_path)

    return jupyter_paths, config_paths


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
    jupyter_paths, jupyter_config_paths = find_jupyter_paths()
    os.environ["JUPYTER_PATH"] = os.pathsep.join(map(str, jupyter_paths))
    os.environ["JUPYTER_CONFIG_PATH"] = os.pathsep.join(map(str, jupyter_config_paths))

    # delete this temporary script
    with contextlib.suppress(PermissionError):
        # FIXME: On Windows, a running script cannot be unlinked
        # because it's locked by the process. Therefore, we can't
        # cleanup the file until after the Jupyter server exists
        # like on unix.
        Path(str(__file__)).unlink(missing_ok=True)
