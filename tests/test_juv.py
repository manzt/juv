from __future__ import annotations

import contextlib
import os
import pathlib
import re
import sys

import jupytext
import pytest
from click.testing import CliRunner, Result
from inline_snapshot import snapshot
from jupytext.pandoc import tempfile
from nbformat.v4.nbbase import new_code_cell, new_notebook

from juv import cli
from juv._nbutils import write_ipynb
from juv._pep723 import parse_inline_script_metadata
from juv._run import to_notebook
from juv._uv import uv

SELF_DIR = pathlib.Path(__file__).parent


# Custom TemporaryDirectory for Python < 3.10
# TODO: Use `ignore_cleanup_errors=True` in Python 3.10+  # noqa: TD002, TD003
class TemporaryDirectoryIgnoreErrors(tempfile.TemporaryDirectory):
    def cleanup(self) -> None:
        with contextlib.suppress(Exception):
            super().cleanup()


def invoke(args: list[str], uv_python: str = "3.13") -> Result:
    return CliRunner().invoke(
        cli,
        args,
        env={
            **os.environ,
            "UV_PYTHON": uv_python,
            "JUV_RUN_MODE": "dry",
            "JUV_JUPYTER": "lab",
            "JUV_TZ": "America/New_York",
            "UV_EXCLUDE_NEWER": "2023-02-01T00:00:00-02:00",
        },
    )


@pytest.fixture
def sample_script() -> str:
    return """
# /// script
# dependencies = ["numpy", "pandas"]
# requires-python = ">=3.8"
# ///

import numpy as np
import pandas as pd

print('Hello, world!')
"""


def test_parse_pep723_meta(sample_script: str) -> None:
    meta = parse_inline_script_metadata(sample_script)
    assert meta == snapshot("""\
dependencies = ["numpy", "pandas"]
requires-python = ">=3.8"
""")


def test_parse_pep723_meta_no_meta() -> None:
    script_without_meta = "print('Hello, world!')"
    assert parse_inline_script_metadata(script_without_meta) is None


def filter_ids(output: str) -> str:
    return re.sub(r'"id": "[a-zA-Z0-9-]+"', '"id": "<ID>"', output)


def test_to_notebook_script(tmp_path: pathlib.Path) -> None:
    script = tmp_path / "script.py"
    script.write_text("""# /// script
# dependencies = ["numpy"]
# requires-python = ">=3.8"
# ///


import numpy as np

# %%
print('Hello, numpy!')
arr = np.array([1, 2, 3])""")

    meta, nb = to_notebook(script)
    output = jupytext.writes(nb, fmt="ipynb")
    output = filter_ids(output)

    assert (meta, output) == snapshot(
        (
            """\
# /// script
# dependencies = ["numpy"]
# requires-python = ">=3.8"
# ///\
""",
            """\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# dependencies = [\\"numpy\\"]\\n",
    "# requires-python = \\">=3.8\\"\\n",
    "# ///"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {},
   "outputs": [],
   "source": [
    "import numpy as np"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {},
   "outputs": [],
   "source": [
    "print('Hello, numpy!')\\n",
    "arr = np.array([1, 2, 3])"
   ]
  }
 ],
 "metadata": {
  "jupytext": {
   "cell_metadata_filter": "-all",
   "main_language": "python",
   "notebook_metadata_filter": "-all"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}\
""",
        ),
    )


def test_run_no_notebook(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = invoke(["run", "test.ipynb"])
    assert result.exit_code == 2  # noqa: PLR2004
    assert result.stdout == snapshot("""\
Usage: cli run [OPTIONS] FILE [JUPYTER_ARGS]...
Try 'cli run --help' for help.

Error: Invalid value for 'FILE': Path 'test.ipynb' does not exist.
""")


def test_run_basic(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "test.ipynb"])
    result = invoke(["run", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("uv run --no-project --with=jupyterlab -\n")


def test_run_python_override(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "test.ipynb"])

    result = invoke(["run", "--python=3.12", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot(
        "uv run --no-project --python=3.12 --with=jupyterlab -\n"
    )


def test_run_with_script_meta(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "test.ipynb", "--with", "numpy"])
    result = invoke(["run", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("uv run --no-project --with=jupyterlab -\n")


def test_run_with_script_meta_and_with_args(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "test.ipynb", "--with", "numpy"])
    result = invoke(["run", "--with", "polars", "--with=anywidget,foo", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot(
        "uv run --no-project --with=jupyterlab --with=polars,anywidget,foo -\n"
    )


def test_run_nbclassic(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "--with", "numpy", "test.ipynb"])
    result = invoke(["run", "--with=polars", "--jupyter=nbclassic", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot(
        "uv run --no-project --with=nbclassic --with=polars -\n"
    )


def test_run_notebook_and_version(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "test.ipynb", "--python=3.8"])
    result = invoke(["run", "--jupyter=notebook@6.4.0", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot(
        "uv run --no-project --with=notebook==6.4.0,setuptools -\n"
    )


def test_run_with_extra_jupyter_flags(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "test.ipynb"])
    result = invoke(
        [
            "run",
            "test.ipynb",
            "--",
            "--no-browser",
            "--port=8888",
            "--ip=0.0.0.0",
        ]
    )
    assert result.exit_code == 0
    assert result.stdout == snapshot("uv run --no-project --with=jupyterlab -\n")


def test_run_uses_version_specifier(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    script = """
# /// script
# dependencies = ["numpy", "pandas"]
# requires-python = ">=3.8,<3.10"
# ///

import numpy as np
import pandas as pd

print('Hello, world!')
"""
    script_path = tmp_path / "script.py"
    script_path.write_text(script)

    foo = to_notebook(script_path)
    write_ipynb(foo[1], tmp_path / "script.ipynb")

    result = invoke(["run", "script.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("uv run --no-project --with=jupyterlab -\n")


def filter_tempfile_ipynb(output: str) -> str:
    """Replace the temporary directory in the output with <TEMPDIR> for snapshotting."""
    pattern = r"`([^`\n]+\n?[^`\n]+/)([^/\n]+\.ipynb)`"
    replacement = r"`<TEMPDIR>/\2`"
    return re.sub(pattern, replacement, output)


def test_add_creates_inline_meta(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    nb = tmp_path / "foo.ipynb"
    write_ipynb(new_notebook(), nb)
    result = invoke(["add", str(nb), "polars==1", "anywidget"], uv_python="3.11")
    assert result.exit_code == 0
    assert filter_tempfile_ipynb(result.stdout) == snapshot("Updated `foo.ipynb`\n")
    assert filter_ids(nb.read_text(encoding="utf-8")) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# requires-python = \\">=3.11\\"\\n",
    "# dependencies = [\\n",
    "#     \\"anywidget\\",\\n",
    "#     \\"polars==1\\",\\n",
    "# ]\\n",
    "# ///"
   ]
  }
 ],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def test_add_prepends_script_meta(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "empty.ipynb"
    write_ipynb(
        new_notebook(cells=[new_code_cell("print('Hello, world!')")]),
        path,
    )
    result = invoke(["add", str(path), "polars==1", "anywidget"], uv_python="3.10")
    assert result.exit_code == 0
    assert filter_tempfile_ipynb(result.stdout) == snapshot("Updated `empty.ipynb`\n")
    assert filter_ids(path.read_text(encoding="utf-8")) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# requires-python = \\">=3.10\\"\\n",
    "# dependencies = [\\n",
    "#     \\"anywidget\\",\\n",
    "#     \\"polars==1\\",\\n",
    "# ]\\n",
    "# ///"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {},
   "outputs": [],
   "source": [
    "print('Hello, world!')"
   ]
  }
 ],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def test_add_updates_existing_meta(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "empty.ipynb"
    nb = new_notebook(
        cells=[
            new_code_cell("""# /// script
# dependencies = ["numpy"]
# requires-python = ">=3.8"
# ///
import numpy as np
print('Hello, numpy!')"""),
        ],
    )
    write_ipynb(nb, path)
    result = invoke(["add", str(path), "polars==1", "anywidget"], uv_python="3.13")
    assert result.exit_code == 0
    assert filter_tempfile_ipynb(result.stdout) == snapshot("Updated `empty.ipynb`\n")
    assert filter_ids(path.read_text(encoding="utf-8")) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {},
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# dependencies = [\\n",
    "#     \\"anywidget\\",\\n",
    "#     \\"numpy\\",\\n",
    "#     \\"polars==1\\",\\n",
    "# ]\\n",
    "# requires-python = \\">=3.8\\"\\n",
    "# ///\\n",
    "import numpy as np\\n",
    "print('Hello, numpy!')"
   ]
  }
 ],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def test_init_creates_notebook_with_inline_meta(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "empty.ipynb"
    result = invoke(["init", str(path)], uv_python="3.13")
    assert result.exit_code == 0
    assert filter_tempfile_ipynb(result.stdout) == snapshot(
        "Initialized notebook at `empty.ipynb`\n"
    )
    assert filter_ids(path.read_text(encoding="utf-8")) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# requires-python = \\">=3.13\\"\\n",
    "# dependencies = []\\n",
    "# ///"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def test_init_creates_notebook_with_specific_python_version(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "empty.ipynb"
    result = invoke(["init", str(path), "--python=3.8"])
    assert result.exit_code == 0
    assert filter_tempfile_ipynb(result.stdout) == snapshot(
        "Initialized notebook at `empty.ipynb`\n"
    )
    assert filter_ids(path.read_text(encoding="utf-8")) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# requires-python = \\">=3.8\\"\\n",
    "# dependencies = []\\n",
    "# ///"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def test_init_with_deps(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    result = invoke(
        [
            "init",
            "--with",
            "rich,requests",
            "--with=polars==1",
            "--with=anywidget[dev]",
            "--with=numpy,pandas>=2",
        ],
    )
    assert result.exit_code == 0
    assert result.stdout == snapshot("Initialized notebook at `Untitled.ipynb`\n")

    path = tmp_path / "Untitled.ipynb"
    assert filter_ids(path.read_text(encoding="utf-8")) == snapshot("""\
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {
    "jupyter": {
     "source_hidden": true
    }
   },
   "outputs": [],
   "source": [
    "# /// script\\n",
    "# requires-python = \\">=3.13\\"\\n",
    "# dependencies = [\\n",
    "#     \\"anywidget[dev]\\",\\n",
    "#     \\"numpy\\",\\n",
    "#     \\"pandas>=2\\",\\n",
    "#     \\"polars==1\\",\\n",
    "#     \\"requests\\",\\n",
    "#     \\"rich\\",\\n",
    "# ]\\n",
    "# ///"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "<ID>",
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def extract_meta_cell(notebook_path: pathlib.Path) -> str:
    nb = jupytext.read(notebook_path)
    return "".join(nb.cells[0].source)


def test_add_with_extras(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    result = invoke(
        [
            "add",
            "test.ipynb",
            "--extra",
            "dev",
            "--extra",
            "foo",
            "anywidget",
        ]
    )

    assert result.exit_code == 0
    assert result.stdout == snapshot("Updated `test.ipynb`\n")
    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "anywidget[dev,foo]",
# ]
# ///\
""")


def test_add_local_package(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    uv(["init", "--lib", "foo"], check=True)
    invoke(["init", "test.ipynb"])
    result = invoke(["add", "test.ipynb", "./foo"])

    assert result.exit_code == 0
    assert result.stdout == snapshot("Updated `test.ipynb`\n")
    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "foo",
# ]
#
# [tool.uv.sources]
# foo = { path = "foo" }
# ///\
""")


def test_add_local_package_as_editable(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    uv(["init", "--lib", "foo"], check=True)
    invoke(["init", "test.ipynb"])
    result = invoke(["add", "test.ipynb", "--editable", "./foo"])

    assert result.exit_code == 0
    assert result.stdout == snapshot("Updated `test.ipynb`\n")
    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "foo",
# ]
#
# [tool.uv.sources]
# foo = { path = "foo", editable = true }
# ///\
""")


def test_add_git_default(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    result = invoke(["add", "test.ipynb", "git+https://github.com/encode/httpx"])

    assert result.exit_code == 0
    assert result.stdout == snapshot("Updated `test.ipynb`\n")
    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx",
# ]
#
# [tool.uv.sources]
# httpx = { git = "https://github.com/encode/httpx" }
# ///\
""")


def test_add_git_tag(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    result = invoke(
        [
            "add",
            "test.ipynb",
            "git+https://github.com/encode/httpx",
            "--tag",
            "0.19.0",
        ]
    )

    assert result.exit_code == 0
    assert result.stdout == snapshot("Updated `test.ipynb`\n")
    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx",
# ]
#
# [tool.uv.sources]
# httpx = { git = "https://github.com/encode/httpx", tag = "0.19.0" }
# ///\
""")


def test_add_git_branch(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    result = invoke(
        [
            "add",
            "test.ipynb",
            "git+https://github.com/encode/httpx",
            "--branch",
            "master",
        ]
    )

    assert result.exit_code == 0
    assert result.stdout == snapshot("Updated `test.ipynb`\n")
    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx",
# ]
#
# [tool.uv.sources]
# httpx = { git = "https://github.com/encode/httpx", branch = "master" }
# ///\
""")


def test_add_git_rev(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    result = invoke(
        [
            "add",
            "test.ipynb",
            "git+https://github.com/encode/httpx",
            "--rev",
            "326b9431c761e1ef1e00b9f760d1f654c8db48c6",
        ]
    )

    assert result.exit_code == 0
    assert result.stdout == snapshot("Updated `test.ipynb`\n")
    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx",
# ]
#
# [tool.uv.sources]
# httpx = { git = "https://github.com/encode/httpx", rev = "326b9431c761e1ef1e00b9f760d1f654c8db48c6" }
# ///\
""")


@pytest.mark.skipif(sys.version_info < (3, 9), reason="Requires Python 3.9 or higher")
def test_stamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # we need to run these tests in this folder because it uses the git history

    with TemporaryDirectoryIgnoreErrors(dir=SELF_DIR) as tmpdir:
        tmp_path = pathlib.Path(tmpdir)
        monkeypatch.chdir(tmp_path)

        invoke(["init", "test.ipynb"])
        result = invoke(
            ["stamp", "test.ipynb", "--timestamp", "2020-01-03 00:00:00-02:00"]
        )

        assert result.exit_code == 0
        assert result.stdout == snapshot(
            "Stamped `test.ipynb` with 2020-01-03T00:00:00-02:00\n"
        )
        assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = []
#
# [tool.uv]
# exclude-newer = "2020-01-03T00:00:00-02:00"
# ///\
""")


@pytest.mark.skipif(sys.version_info < (3, 9), reason="Requires Python 3.9 or higher")
def test_stamp_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # we need to run these tests in this folder because it uses the git history

    with TemporaryDirectoryIgnoreErrors(dir=SELF_DIR) as tmpdir:
        tmp_path = pathlib.Path(tmpdir)
        monkeypatch.chdir(tmp_path)

        with (tmp_path / "foo.py").open("w", encoding="utf-8") as f:
            f.write("""# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///


def main() -> None:
    print("Hello from foo.py!")


if __name__ == "__main__":
    main()
""")
        result = invoke(["stamp", "foo.py", "--date", "2006-01-02"])

        assert result.exit_code == 0
        assert result.stdout == snapshot(
            "Stamped `foo.py` with 2006-01-03T00:00:00-05:00\n"
        )
        assert (tmp_path / "foo.py").read_text(encoding="utf-8") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = []
#
# [tool.uv]
# exclude-newer = "2006-01-03T00:00:00-05:00"
# ///


def main() -> None:
    print("Hello from foo.py!")


if __name__ == "__main__":
    main()
""")


@pytest.mark.skipif(sys.version_info < (3, 9), reason="Requires Python 3.9 or higher")
def test_stamp_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # we need to run these tests in this folder because it uses the git history

    with TemporaryDirectoryIgnoreErrors(dir=SELF_DIR) as tmpdir:
        tmp_path = pathlib.Path(tmpdir)
        monkeypatch.chdir(tmp_path)

        with (tmp_path / "foo.py").open("w", encoding="utf-8") as f:
            f.write("""# /// script
# requires-python = ">=3.13"
# dependencies = []
#
# [tool.uv]
# exclude-newer = "blah"
# ///
""")

        result = invoke(["stamp", "foo.py", "--clear"])

        assert result.exit_code == 0
        assert result.stdout == snapshot("Removed blah from `foo.py`\n")
        assert (tmp_path / "foo.py").read_text(encoding="utf-8") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
""")


def test_add_notebook_pinned(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    result = invoke(["add", "test.ipynb", "anywidget", "--pin"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("Updated `test.ipynb`\n")
    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "anywidget==0.1.0",
# ]
# ///\
""")


def test_add_script_pinned(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    with (tmp_path / "foo.py").open("w", encoding="utf-8") as f:
        f.write("""# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///

print("Hello from foo.py!")
""")

    result = invoke(["add", "foo.py", "anywidget", "--pin"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("Updated `foo.py`\n")
    assert (tmp_path / "foo.py").read_text(encoding="utf-8") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "anywidget==0.1.0",
# ]
# ///

print("Hello from foo.py!")
""")
