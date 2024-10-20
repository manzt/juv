import pytest
from pathlib import Path
import sys
from unittest.mock import patch
import pathlib
import re
from inline_snapshot import snapshot

import juv
from juv import Pep723Meta
import jupytext


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


@pytest.fixture
def sample_notebook() -> dict:
    return {
        "cells": [
            {
                "cell_type": "code",
                "source": "# /// script\n# dependencies = [\"pandas\"]\n# ///\n\nimport pandas as pd\nprint('Hello, pandas!')",
            }
        ],
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def test_parse_pep723_meta(sample_script: str) -> None:
    meta = juv.parse_pep723_meta(sample_script)
    assert isinstance(meta, juv.Pep723Meta)
    assert meta.dependencies == ["numpy", "pandas"]
    assert meta.requires_python == ">=3.8"


def test_parse_pep723_meta_no_meta() -> None:
    script_without_meta = "print('Hello, world!')"
    assert juv.parse_pep723_meta(script_without_meta) is None


def test_to_notebook_script(tmp_path: pathlib.Path):
    script = tmp_path / "script.py"
    script.write_text("""# /// script
# dependencies = ["numpy"]
# requires-python = ">=3.8"
# ///


import numpy as np

# %%
print('Hello, numpy!')
arr = np.array([1, 2, 3])""")

    meta, nb = juv.to_notebook(script)
    output = jupytext.writes(nb, fmt="ipynb")
    output = re.sub(r'"id": "[a-zA-Z0-9-]+"', '"id": "<ID>"', output)

    assert (meta, output) == snapshot(
        (
            Pep723Meta(dependencies=["numpy"], requires_python=">=3.8"),
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
        )
    )


def test_assert_uv_available() -> None:
    with patch("shutil.which", return_value=None):
        with pytest.raises(SystemExit):
            juv.assert_uv_available()


def test_python_override() -> None:
    assert juv.build_command(
        nb_path=Path("test.ipynb"),
        pep723_meta=Pep723Meta(dependencies=["numpy"], requires_python="3.8"),
        command="nbclassic",
        pre_args=["--with", "polars", "--python", "3.12"],
        command_version=None,
    ) == snapshot(
        [
            "uvx",
            "--from=jupyter-core",
            "--with=setuptools",
            "--with=numpy",
            "--with=nbclassic",
            "--with",
            "polars",
            "--python",
            "3.12",
            "jupyter",
            "nbclassic",
            "test.ipynb",
        ]
    )


def test_run_nbclassic() -> None:
    assert juv.build_command(
        nb_path=Path("test.ipynb"),
        pep723_meta=Pep723Meta(dependencies=["numpy"], requires_python="3.8"),
        command="nbclassic",
        pre_args=["--with", "polars"],
        command_version=None,
    ) == snapshot(
        [
            "uvx",
            "--from=jupyter-core",
            "--with=setuptools",
            "--python=3.8",
            "--with=numpy",
            "--with=nbclassic",
            "--with",
            "polars",
            "jupyter",
            "nbclassic",
            "test.ipynb",
        ]
    )


def test_run_notebook() -> None:
    assert juv.build_command(
        nb_path=Path("test.ipynb"),
        pep723_meta=Pep723Meta(dependencies=["numpy"], requires_python="3.8"),
        command="notebook",
        pre_args=[],
        command_version="6.4.0",
    ) == snapshot(
        [
            "uvx",
            "--from=jupyter-core",
            "--with=setuptools",
            "--python=3.8",
            "--with=numpy",
            "--with=notebook==6.4.0",
            "jupyter",
            "notebook",
            "test.ipynb",
        ]
    )


def test_run_jlab() -> None:
    assert juv.build_command(
        nb_path=Path("test.ipynb"),
        pep723_meta=Pep723Meta(dependencies=["numpy"], requires_python="3.8"),
        command="lab",
        pre_args=["--with=polars,altair"],
        command_version=None,
    ) == snapshot(
        [
            "uvx",
            "--from=jupyter-core",
            "--with=setuptools",
            "--python=3.8",
            "--with=numpy",
            "--with=jupyterlab",
            "--with=polars,altair",
            "jupyter",
            "lab",
            "test.ipynb",
        ]
    )


def test_split_args_no_pre_args() -> None:
    args = ["juv", "lab", "script.py"]
    with patch.object(sys, "argv", args):
        assert juv.split_args() == snapshot(([], ["lab", "script.py"], None))


def test_split_args_with_command_version() -> None:
    args = ["juv", "notebook@6.4.0", "notebook.ipynb"]
    with patch.object(sys, "argv", args):
        assert juv.split_args() == snapshot(
            (
                [],
                ["notebook", "notebook.ipynb"],
                "6.4.0",
            )
        )


def test_split_args_with_pre_args() -> None:
    args = ["juv", "--with", "polars", "lab", "script.py"]
    with patch.object(sys, "argv", args):
        assert juv.split_args() == snapshot(
            (
                ["--with", "polars"],
                ["lab", "script.py"],
                None,
            )
        )
