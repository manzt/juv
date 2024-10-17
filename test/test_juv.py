import pytest
from pathlib import Path
import json
import tempfile
import sys
from unittest.mock import patch
from inline_snapshot import snapshot

import juv


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
    assert meta.python_version == ">=3.8"


def test_parse_pep723_meta_no_meta() -> None:
    script_without_meta = "print('Hello, world!')"
    assert juv.parse_pep723_meta(script_without_meta) is None


def test_script_to_nb(sample_script: str) -> None:
    nb_json = juv.script_to_nb(sample_script)
    nb = json.loads(nb_json)

    assert nb == snapshot(
        {
            "cells": [
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {"jupyter": {"source_hidden": True}},
                    "outputs": [],
                    "source": """\
# /// script
# dependencies = ["numpy", "pandas"]
# requires-python = ">=3.8"
# ///\
""",
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {"jupyter": {"source_hidden": False}},
                    "outputs": [],
                    "source": """\
import numpy as np
import pandas as pd

print('Hello, world!')\
""",
                },
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                }
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
    )


@pytest.mark.parametrize("file_ext,expected_cells", [(".py", 2), (".ipynb", 1)])
def test_to_notebook(file_ext, expected_cells, sample_script, sample_notebook) -> None:
    with tempfile.NamedTemporaryFile(suffix=file_ext, mode="w+") as tf:
        if file_ext == ".py":
            tf.write(sample_script)
        else:
            json.dump(sample_notebook, tf)
        tf.flush()

        meta, content = juv.to_notebook(Path(tf.name))

        assert isinstance(meta, juv.Pep723Meta)
        nb = json.loads(content)
        assert len(nb["cells"]) == expected_cells


def test_assert_uv_available() -> None:
    with patch("shutil.which", return_value=None):
        with pytest.raises(SystemExit):
            juv.assert_uv_available()


def test_python_override() -> None:
    assert juv.build_command(
        nb_path=Path("test.ipynb"),
        pep723_meta=juv.Pep723Meta(dependencies=["numpy"], python_version="3.8"),
        command="nbclassic",
        pre_args=["--with", "polars", "--python", "3.12"],
        command_version=None,
    ) == snapshot(
        [
            "uvx",
            "--from",
            "jupyter-core",
            "--with",
            "setuptools",
            "--with",
            "numpy",
            "--with",
            "nbclassic",
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
        pep723_meta=juv.Pep723Meta(dependencies=["numpy"], python_version="3.8"),
        command="nbclassic",
        pre_args=["--with", "polars"],
        command_version=None,
    ) == snapshot(
        [
            "uvx",
            "--from",
            "jupyter-core",
            "--with",
            "setuptools",
            "--python",
            "3.8",
            "--with",
            "numpy",
            "--with",
            "nbclassic",
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
        pep723_meta=juv.Pep723Meta(dependencies=["numpy"], python_version="3.8"),
        command="notebook",
        pre_args=[],
        command_version="6.4.0",
    ) == snapshot(
        [
            "uvx",
            "--from",
            "jupyter-core",
            "--with",
            "setuptools",
            "--python",
            "3.8",
            "--with",
            "numpy",
            "--with",
            "notebook==6.4.0",
            "jupyter",
            "notebook",
            "test.ipynb",
        ]
    )


def test_run_jlab() -> None:
    assert juv.build_command(
        nb_path=Path("test.ipynb"),
        pep723_meta=juv.Pep723Meta(dependencies=["numpy"], python_version="3.8"),
        command="lab",
        pre_args=["--with", "polars"],
        command_version=None,
    ) == snapshot(
        [
            "uvx",
            "--from",
            "jupyter-core",
            "--with",
            "setuptools",
            "--python",
            "3.8",
            "--with",
            "numpy",
            "--with",
            "jupyterlab",
            "--with",
            "polars",
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
