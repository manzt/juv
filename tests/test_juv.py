from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

import jupytext
import pytest
from click.testing import CliRunner, Result
from inline_snapshot import snapshot
from nbformat.v4.nbbase import new_code_cell, new_notebook

from juv import cli
from juv._nbutils import write_ipynb
from juv._pep723 import parse_inline_script_metadata
from juv._run import to_notebook

if TYPE_CHECKING:
    import pathlib


def invoke(args: list[str], uv_python: str = "3.13") -> Result:
    return CliRunner().invoke(
        cli,
        args,
        env={**os.environ, "UV_PYTHON": uv_python, "JUV_DEBUG": "1"},
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
    assert result.stdout == snapshot(
        "uv run --no-project --with=jupyterlab -\n"
    )


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
    assert result.stdout == snapshot(
        "uv run --no-project --with=jupyterlab -\n"
    )


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
    assert result.stdout == snapshot(
        "uv run --no-project --with=jupyterlab -\n"
    )


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
    assert result.stdout == snapshot(
        "uv run --no-project --with=jupyterlab -\n"
    )


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
    assert filter_ids(nb.read_text()) == snapshot("""\
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
    assert filter_ids(path.read_text()) == snapshot("""\
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
    assert filter_ids(path.read_text()) == snapshot("""\
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
    assert filter_ids(path.read_text()) == snapshot("""\
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
 "metadata": {},
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
    assert filter_ids(path.read_text()) == snapshot("""\
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
 "metadata": {},
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
    assert filter_ids(path.read_text()) == snapshot("""\
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
 "metadata": {},
 "nbformat": 4,
 "nbformat_minor": 5
}\
""")
