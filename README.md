# juv

A toolkit for reproducible Jupyter notebooks, powered by [uv](https://docs.astral.sh/uv/).

## features

- 🗂️ Create, manage, and run reproducible notebooks
- 📌 Pin dependencies with [PEP 723 - inline script metadata](https://peps.python.org/pep-0723)
- 🚀 Launch ephemeral sessions for multiple front ends (e.g., JupyterLab, Notebook, NbClassic)
- ⚡ Powered by [uv](https://docs.astral.sh/uv/) for fast dependency management

## usage

**juv** should feel familar for `uv` users. The goal is to extend its
dependencies management to Jupyter notebooks.

```sh
# create a notebook
juv init notebook.ipynb
juv init --python=3.9 notebook.ipynb # specify a minimum Python version

# add dependencies to the notebook
juv add notebook.ipynb pandas numpy
juv add notebook.ipynb --requirements=requirements.txt

# launch the notebook
juv run notebook.ipynb
juv run --with=polars notebook.ipynb # additional dependencies for this session (not saved)
juv run --jupyter=notebook@6.4.0 notebook.ipynb # pick a specific Jupyter frontend

# JUV_JUPYTER env var to set preferred Jupyter frontend (default: lab)
export JUV_JUPYTER=nbclassic
juv run notebook.ipynb
```

If a script is provided to `run`, it will be converted to a notebook before
launching the Jupyter session.

```sh
uvx juv run script.py
# Converted script to notebook `script.ipynb`
# Launching Jupyter session...
```

## why

[PEP 723 (inline script metadata)](https://peps.python.org/pep-0723) allows
specifying dependencies as comments within Python scripts, enabling
self-contained, reproducible execution. This feature could significantly
improve reproducibility in the data science ecosystem, since many analyses are
shared as standalone code (not packages). However, _a lot_ of data science code
lives in notebooks (`.ipynb` files), not Python scripts (`.py` files).

**juv** bridges this gap by:

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
