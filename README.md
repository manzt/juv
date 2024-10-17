# juv

A little wrapper around `uv` to launch ephemeral Jupyter notebooks.

```sh
uvx juv
# juv [uvx flags] <command>[@version] <path>
#
# Commands:
#   lab       Launch JupyterLab
#   notebook  Launch Jupyter Notebook (classic)
#
# Arguments:
#   path  Path to the Python script or notebook file
#
# Examples:
#   uvx juv lab script.py
#   uvx juv notebook@7.2.2 script.ipynb
#   uvx juv notebook existing_notebook.ipynb
#   uvx juv --with pandas,matplotlib lab new_notebook.ipynb
```

`juv` has two main commands:

- `juv lab` launches a Jupyter Lab session
- `juv notebook` launches a classic notebook session

Both commands accept a single argument: the path to the notebook or script to
launch. A script will be converted to a notebook before launching.

```sh
uvx juv lab script.py # creates script.ipynb
```

Any flags that are passed prior to the command (e.g., `uvx juv --with=polars
lab`) will be forwarded to `uvx` as-is. This allows you to specify additional
dependencies, a different interpreter, etc.

## what

[PEP 723 (inline script metadata)](https://peps.python.org/pep-0723) allows
specifying dependencies as comments within Python scripts, enabling
self-contained, reproducible execution. This feature could significantly
improve reproducibility in the data science ecosystem, since many analyses are
shared as standalone code (not packages). However, _a lot_ of data science code
lives in notebooks (`.ipynb` files), not Python scripts (`.py` files).

`juv` bridges this gap by:

- Extending PEP 723-style metadata support from `uv` to Jupyter notebooks
- Launching Jupyter sessions with the specified dependencies

It's a simple Python script that parses the notebook and starts a Jupyter
session with the specified dependencies (piggybacking on `uv`'s existing
functionality).

## alternatives

`juv` is opinionated and might not suit your preferences. That's ok! `uv` is
super extensible, and I recommend reading [the
documentation](https://docs.astral.sh/uv) to learn about its primitives.

For example, you can achieve a similar workflow using the `--with-requirements`
flag:

```sh
uvx --with-requirements=requirements.txt --from=jupyter-core --with=jupyterlab jupyter lab notebook.ipynb
```

While slightly more verbose, and breaking self-containment, this approach works well.
