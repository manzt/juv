# juv

A little wrapper around `uv` to launch ephemeral Jupyter notebooks.

```sh
uvx juv
# A wrapper around uv to launch ephemeral Jupyter notebooks.
#
# Usage: juv [uvx flags] <COMMAND>[@version] [PATH]
#
# Commands:
#   init: Initialize a new notebook
#   add: Add dependencies to the notebook
#   lab: Launch notebook/script in Jupyter Lab
#   notebook: Launch notebook/script in Jupyter Notebook
#   nbclassic: Launch notebook/script in Jupyter Notebook Classic
#
# Examples:
#   juv init foo.ipynb
#   juv add foo.ipynb numpy pandas
#   juv lab foo.ipynb
#   juv nbclassic script.py
#   juv --python=3.8 notebook@6.4.0 foo.ipynb
```

Scripts will be converted to notebooks before launching the Jupyter session.

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
super extensible, and I recommend reading the wonderful
[documentation](https://docs.astral.sh/uv) to learn about its primitives.

For example, you can achieve a similar workflow using the `--with-requirements`
flag:

```sh
uvx --with-requirements=requirements.txt --from=jupyter-core --with=jupyterlab jupyter lab notebook.ipynb
```

While slightly more verbose and breaking self-containment, this approach
totally works and saves you from installing another dependency.
