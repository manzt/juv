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
    assert result.stdout == snapshot("uv run --no-project --with=jupyterlab --script\n")


def test_run_python_override(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "test.ipynb"])

    result = invoke(["run", "--python=3.12", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot(
        "uv run --no-project --python=3.12 --with=jupyterlab --script\n"
    )


def test_run_with_script_meta(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "test.ipynb", "--with", "numpy"])
    result = invoke(["run", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("uv run --no-project --with=jupyterlab --script\n")


def test_run_with_script_meta_and_with_args(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "test.ipynb", "--with", "numpy"])
    result = invoke(["run", "--with", "polars", "--with=anywidget,foo", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot(
        "uv run --no-project --with=jupyterlab --with=polars,anywidget,foo --script\n"
    )


def test_run_nbclassic(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "--with", "numpy", "test.ipynb"])
    result = invoke(["run", "--with=polars", "--jupyter=nbclassic", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot(
        "uv run --no-project --with=nbclassic --with=polars --script\n"
    )


def test_run_notebook_and_version(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    invoke(["init", "test.ipynb", "--python=3.8"])
    result = invoke(["run", "--jupyter=notebook@6.4.0", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot(
        "uv run --no-project --with=notebook==6.4.0,setuptools --script\n"
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
    assert result.stdout == snapshot("uv run --no-project --with=jupyterlab --script\n")


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
    assert result.stdout == snapshot("uv run --no-project --with=jupyterlab --script\n")


def filter_tempfile_ipynb(output: str) -> str:
    """Replace the temporary directory in the output with <TEMPDIR> for snapshotting."""
    pattern = r"`([^`\n]+\n?[^`\n]+/)([^/\n]+\.ipynb)`"
    replacement = r"`<TEMPDIR>/\2`"
    return re.sub(pattern, replacement, output)


def test_add_index(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    nb = tmp_path / "foo.ipynb"
    write_ipynb(new_notebook(), nb)
    result = invoke(
        [
            "add",
            str(nb),
            "polars",
            "--index",
            "https://pip.repos.neuron.amazonaws.com",
        ]
    )
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
    "# requires-python = \\">=3.13\\"\\n",
    "# dependencies = [\\n",
    "#     \\"polars\\",\\n",
    "# ]\\n",
    "#\\n",
    "# [[tool.uv.index]]\\n",
    "# url = \\"https://pip.repos.neuron.amazonaws.com/\\"\\n",
    "# ///"
   ]
  }
 ],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


def test_add_default_index(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    nb = tmp_path / "foo.ipynb"
    write_ipynb(new_notebook(), nb)
    result = invoke(
        [
            "add",
            str(nb),
            "polars",
            "--default-index",
            "https://pip.repos.neuron.amazonaws.com",
        ]
    )
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
    "# requires-python = \\">=3.13\\"\\n",
    "# dependencies = [\\n",
    "#     \\"polars\\",\\n",
    "# ]\\n",
    "#\\n",
    "# [[tool.uv.index]]\\n",
    "# url = \\"https://pip.repos.neuron.amazonaws.com/\\"\\n",
    "# default = true\\n",
    "# ///"
   ]
  }
 ],
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")


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


@pytest.mark.skip(reason="Currently too flaky to run in CI")
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


@pytest.mark.skip(reason="Currently too flaky to run in CI")
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


@pytest.mark.skip(reason="Currently too flaky to run in CI")
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


@pytest.mark.skip(reason="Currently too flaky to run in CI")
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


def test_remove(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    result = invoke(
        ["add", "test.ipynb", "anywidget", "numpy==1.21.0", "polars==1.0.0"]
    )
    assert result.exit_code == 0
    assert result.stdout == snapshot("Updated `test.ipynb`\n")
    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "anywidget",
#     "numpy==1.21.0",
#     "polars==1.0.0",
# ]
# ///\
""")

    result = invoke(["remove", "test.ipynb", "anywidget", "polars"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("Updated `test.ipynb`\n")
    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "numpy==1.21.0",
# ]
# ///\
""")


def test_lock(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    invoke(["add", "test.ipynb", "polars"])
    result = invoke(["lock", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("Locked `test.ipynb`\n")

    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "polars",
# ]
# ///\
""")

    nb = jupytext.read(tmp_path / "test.ipynb")
    assert nb.metadata["uv.lock"] == snapshot("""\
version = 1
revision = 1
requires-python = ">=3.13"

[options]
exclude-newer = "2023-02-01T02:00:00Z"

[manifest]
requirements = [{ name = "polars" }]

[[package]]
name = "polars"
version = "0.16.1"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files.pythonhosted.org/packages/a2/6d/e34f5677393a986b5a6b0b8284da31154bdf0ed55a1feffc73cc8c0dfa4e/polars-0.16.1.tar.gz", hash = "sha256:ebba7a51581084adb85dde10579b1dd8b648f7c5ca38a6839eee64d2e4827612", size = 1352066 }
wheels = [
    { url = "https://files.pythonhosted.org/packages/4d/aa/ecf2df7468dab00f8ad7b5fdcd834ca4bffee8e6095e011153c9d82d5df0/polars-0.16.1-cp37-abi3-macosx_10_7_x86_64.whl", hash = "sha256:180172c8db33f950b3f2ff7793d2cf3de9d3ad9b13c5f0181cda0ac3e7db5977", size = 14844819 },
    { url = "https://files.pythonhosted.org/packages/f2/c5/f19a2b3f1d3251615ee136fb03f251eb00e4566688afa3b84f0d1cb4f4d3/polars-0.16.1-cp37-abi3-macosx_11_0_arm64.whl", hash = "sha256:6c391546a158233172589ce810fcafd71a60d776add8421364bdd5ff05af2cd9", size = 12930182 },
    { url = "https://files.pythonhosted.org/packages/32/bc/5f674384f48dfad969a634918487dc0b207ee08702d57433d24d0da6a3fb/polars-0.16.1-cp37-abi3-manylinux_2_17_aarch64.manylinux2014_aarch64.whl", hash = "sha256:e2096a1384a5fecf003bb3915264212c63d1c43e8790126ee8fcdd682f1782ac", size = 13382356 },
    { url = "https://files.pythonhosted.org/packages/7e/82/ee89b63d8cd638d12b79515fb0c63d602ca8fc5eb8d1c4b6b9f690a1a02d/polars-0.16.1-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", hash = "sha256:934bca853a0086a30800c40ac615578894531b378afc1ba4c1a7e15855218c64", size = 15291186 },
    { url = "https://files.pythonhosted.org/packages/d8/4d/3b371736693c952b616dac469d91fb9a42217758bf0f79ac4170c032069d/polars-0.16.1-cp37-abi3-win_amd64.whl", hash = "sha256:a670586eee6fad98a2daafbe3f6dfc845b35a22e44bc4daaca93d4f0f4d05229", size = 16264469 },
]
""")


def test_add_updates_lock(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    result = invoke(["lock", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("Locked `test.ipynb`\n")
    assert extract_meta_cell(tmp_path / "test.ipynb") == snapshot("""\
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///\
""")
    assert jupytext.read(tmp_path / "test.ipynb").metadata["uv.lock"] == snapshot("""\
version = 1
revision = 1
requires-python = ">=3.13"

[options]
exclude-newer = "2023-02-01T02:00:00Z"
""")

    result = invoke(["add", "test.ipynb", "polars"])
    assert result.exit_code == 0
    assert jupytext.read(tmp_path / "test.ipynb").metadata["uv.lock"] == snapshot("""\
version = 1
revision = 1
requires-python = ">=3.13"

[options]
exclude-newer = "2023-02-01T02:00:00Z"

[manifest]
requirements = [{ name = "polars", specifier = ">=0.16.1" }]

[[package]]
name = "polars"
version = "0.16.1"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files.pythonhosted.org/packages/a2/6d/e34f5677393a986b5a6b0b8284da31154bdf0ed55a1feffc73cc8c0dfa4e/polars-0.16.1.tar.gz", hash = "sha256:ebba7a51581084adb85dde10579b1dd8b648f7c5ca38a6839eee64d2e4827612", size = 1352066 }
wheels = [
    { url = "https://files.pythonhosted.org/packages/4d/aa/ecf2df7468dab00f8ad7b5fdcd834ca4bffee8e6095e011153c9d82d5df0/polars-0.16.1-cp37-abi3-macosx_10_7_x86_64.whl", hash = "sha256:180172c8db33f950b3f2ff7793d2cf3de9d3ad9b13c5f0181cda0ac3e7db5977", size = 14844819 },
    { url = "https://files.pythonhosted.org/packages/f2/c5/f19a2b3f1d3251615ee136fb03f251eb00e4566688afa3b84f0d1cb4f4d3/polars-0.16.1-cp37-abi3-macosx_11_0_arm64.whl", hash = "sha256:6c391546a158233172589ce810fcafd71a60d776add8421364bdd5ff05af2cd9", size = 12930182 },
    { url = "https://files.pythonhosted.org/packages/32/bc/5f674384f48dfad969a634918487dc0b207ee08702d57433d24d0da6a3fb/polars-0.16.1-cp37-abi3-manylinux_2_17_aarch64.manylinux2014_aarch64.whl", hash = "sha256:e2096a1384a5fecf003bb3915264212c63d1c43e8790126ee8fcdd682f1782ac", size = 13382356 },
    { url = "https://files.pythonhosted.org/packages/7e/82/ee89b63d8cd638d12b79515fb0c63d602ca8fc5eb8d1c4b6b9f690a1a02d/polars-0.16.1-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", hash = "sha256:934bca853a0086a30800c40ac615578894531b378afc1ba4c1a7e15855218c64", size = 15291186 },
    { url = "https://files.pythonhosted.org/packages/d8/4d/3b371736693c952b616dac469d91fb9a42217758bf0f79ac4170c032069d/polars-0.16.1-cp37-abi3-win_amd64.whl", hash = "sha256:a670586eee6fad98a2daafbe3f6dfc845b35a22e44bc4daaca93d4f0f4d05229", size = 16264469 },
]
""")


def test_remove_updates_lock(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    invoke(["add", "test.ipynb", "polars"])
    result = invoke(["lock", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("Locked `test.ipynb`\n")
    assert jupytext.read(tmp_path / "test.ipynb").metadata["uv.lock"] == snapshot("""\
version = 1
revision = 1
requires-python = ">=3.13"

[options]
exclude-newer = "2023-02-01T02:00:00Z"

[manifest]
requirements = [{ name = "polars" }]

[[package]]
name = "polars"
version = "0.16.1"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files.pythonhosted.org/packages/a2/6d/e34f5677393a986b5a6b0b8284da31154bdf0ed55a1feffc73cc8c0dfa4e/polars-0.16.1.tar.gz", hash = "sha256:ebba7a51581084adb85dde10579b1dd8b648f7c5ca38a6839eee64d2e4827612", size = 1352066 }
wheels = [
    { url = "https://files.pythonhosted.org/packages/4d/aa/ecf2df7468dab00f8ad7b5fdcd834ca4bffee8e6095e011153c9d82d5df0/polars-0.16.1-cp37-abi3-macosx_10_7_x86_64.whl", hash = "sha256:180172c8db33f950b3f2ff7793d2cf3de9d3ad9b13c5f0181cda0ac3e7db5977", size = 14844819 },
    { url = "https://files.pythonhosted.org/packages/f2/c5/f19a2b3f1d3251615ee136fb03f251eb00e4566688afa3b84f0d1cb4f4d3/polars-0.16.1-cp37-abi3-macosx_11_0_arm64.whl", hash = "sha256:6c391546a158233172589ce810fcafd71a60d776add8421364bdd5ff05af2cd9", size = 12930182 },
    { url = "https://files.pythonhosted.org/packages/32/bc/5f674384f48dfad969a634918487dc0b207ee08702d57433d24d0da6a3fb/polars-0.16.1-cp37-abi3-manylinux_2_17_aarch64.manylinux2014_aarch64.whl", hash = "sha256:e2096a1384a5fecf003bb3915264212c63d1c43e8790126ee8fcdd682f1782ac", size = 13382356 },
    { url = "https://files.pythonhosted.org/packages/7e/82/ee89b63d8cd638d12b79515fb0c63d602ca8fc5eb8d1c4b6b9f690a1a02d/polars-0.16.1-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", hash = "sha256:934bca853a0086a30800c40ac615578894531b378afc1ba4c1a7e15855218c64", size = 15291186 },
    { url = "https://files.pythonhosted.org/packages/d8/4d/3b371736693c952b616dac469d91fb9a42217758bf0f79ac4170c032069d/polars-0.16.1-cp37-abi3-win_amd64.whl", hash = "sha256:a670586eee6fad98a2daafbe3f6dfc845b35a22e44bc4daaca93d4f0f4d05229", size = 16264469 },
]
""")

    invoke(["remove", "test.ipynb", "polars"])
    assert result.exit_code == 0
    assert jupytext.read(tmp_path / "test.ipynb").metadata["uv.lock"] == snapshot("""\
version = 1
revision = 1
requires-python = ">=3.13"

[options]
exclude-newer = "2023-02-01T02:00:00Z"
""")


def test_tree(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    invoke(["add", "test.ipynb", "rich"])
    result = invoke(["tree", "test.ipynb"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("""\
rich v13.3.1
├── markdown-it-py v2.1.0
│   └── mdurl v0.1.2
└── pygments v2.14.0
""")


def test_clear_lock(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    invoke(["add", "test.ipynb", "attrs"])
    invoke(["lock", "test.ipynb"])
    assert jupytext.read(tmp_path / "test.ipynb").metadata.get("uv.lock") == snapshot("""\
version = 1
revision = 1
requires-python = ">=3.13"

[options]
exclude-newer = "2023-02-01T02:00:00Z"

[manifest]
requirements = [{ name = "attrs" }]

[[package]]
name = "attrs"
version = "22.2.0"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files.pythonhosted.org/packages/21/31/3f468da74c7de4fcf9b25591e682856389b3400b4b62f201e65f15ea3e07/attrs-22.2.0.tar.gz", hash = "sha256:c9227bfc2f01993c03f68db37d1d15c9690188323c067c641f1a35ca58185f99", size = 215900 }
wheels = [
    { url = "https://files.pythonhosted.org/packages/fb/6e/6f83bf616d2becdf333a1640f1d463fef3150e2e926b7010cb0f81c95e88/attrs-22.2.0-py3-none-any.whl", hash = "sha256:29e95c7f6778868dbd49170f98f8818f78f3dc5e0e37c0b1f474e3561b240836", size = 60018 },
]
""")

    result = invoke(["lock", "test.ipynb", "--clear"])
    assert result.exit_code == 0
    assert result.stdout == snapshot("Cleared lockfile `test.ipynb`\n")
    assert jupytext.read(tmp_path / "test.ipynb").metadata.get("uv.lock") is None


def sanitize_uv_export_command(output: str) -> str:
    """Replace the temporary file path after 'uv export --script' with <TEMPFILE>"""
    pattern = r"(uv export --script )([^\s]+[\\/][^\s]+\.py)"
    replacement = r"\1<TEMPFILE>"
    return re.sub(pattern, replacement, output)


def test_export(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    invoke(["add", "test.ipynb", "attrs"])
    result = invoke(["export", "test.ipynb"])
    assert result.exit_code == 0
    assert sanitize_uv_export_command(result.stdout) == snapshot("""\
# This file was autogenerated by uv via the following command:
#    uv export --script <TEMPFILE>
attrs==22.2.0 \\
    --hash=sha256:29e95c7f6778868dbd49170f98f8818f78f3dc5e0e37c0b1f474e3561b240836 \\
    --hash=sha256:c9227bfc2f01993c03f68db37d1d15c9690188323c067c641f1a35ca58185f99
""")


@pytest.mark.parametrize("command", ["export", "tree"])
def test_commands_update_lock(
    command: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    invoke(["init", "test.ipynb"])
    invoke(["lock", "test.ipynb"])
    invoke(["add", "test.ipynb", "attrs"])
    invoke([command, "test.ipynb"])
    notebook = jupytext.read(tmp_path / "test.ipynb")
    assert notebook.metadata["uv.lock"] == snapshot("""\
version = 1
revision = 1
requires-python = ">=3.13"

[options]
exclude-newer = "2023-02-01T02:00:00Z"

[manifest]
requirements = [{ name = "attrs", specifier = ">=22.2.0" }]

[[package]]
name = "attrs"
version = "22.2.0"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files.pythonhosted.org/packages/21/31/3f468da74c7de4fcf9b25591e682856389b3400b4b62f201e65f15ea3e07/attrs-22.2.0.tar.gz", hash = "sha256:c9227bfc2f01993c03f68db37d1d15c9690188323c067c641f1a35ca58185f99", size = 215900 }
wheels = [
    { url = "https://files.pythonhosted.org/packages/fb/6e/6f83bf616d2becdf333a1640f1d463fef3150e2e926b7010cb0f81c95e88/attrs-22.2.0-py3-none-any.whl", hash = "sha256:29e95c7f6778868dbd49170f98f8818f78f3dc5e0e37c0b1f474e3561b240836", size = 60018 },
]
""")

    notebook.cells[0] = new_code_cell("""# /// script
# dependencies = []
# requires-python = ">=3.8"
# ///
""")
    write_ipynb(notebook, tmp_path / "test.ipynb")
    invoke([command, "test.ipynb"])
    assert jupytext.read(tmp_path / "test.ipynb").metadata["uv.lock"] == snapshot("""\
version = 1
revision = 1
requires-python = ">=3.8"

[options]
exclude-newer = "2023-02-01T02:00:00Z"
""")
