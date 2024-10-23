# juv

[![version](https://img.shields.io/pypi/v/juv.svg?labelColor=0273B7&color=0C3141)](https://pypi.org/pypi/juv)
[![license](https://img.shields.io/pypi/l/juv.svg)](https://github.com/manzt/juv/blob/main/LICENSE)
[![python versions](https://img.shields.io/pypi/pyversions/juv.svg)](https://pypi.python.org/pypi/juv)
[![Actions status](https://github.com/manzt/juv/actions/workflows/ci.yml/badge.svg)](https://github.com/manzt/juv/actions)

A toolkit for reproducible Jupyter notebooks, powered by [uv](https://docs.astral.sh/uv/).

## Features

- 🗂️ Create, manage, and run reproducible notebooks
- 📌 Pin dependencies with [PEP 723 - inline script metadata](https://peps.python.org/pep-0723)
- 🚀 Launch ephemeral sessions for multiple front ends (e.g., JupyterLab, Notebook, NbClassic)
- ⚡ Powered by [uv](https://docs.astral.sh/uv/) for fast dependency management

## Installation

**juv** is published to the Python Package Index (PyPI) and can be installed
globally with `uv` or `pipx` (recommended):

```sh
uv tool install juv
# or pipx install juv
```

You can also use the [`uvx`](https://docs.astral.sh/uv/guides/tools/) command
to invoke it without installing:

```sh
uvx juv
```

## Usage

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

## Motivation

_Rethinking the "getting started" guide for notebooks_

Jupyter notebooks are the de facto standard for data science, yet they suffer
from a [reproducibility
crisis](https://leomurta.github.io/papers/pimentel2019a.pdf).

This issue does not stem from a fundamental lack of care for reproducibility.
Rather, our tools limit us from easily falling into the [pit of
success](https://blog.codinghorror.com/falling-into-the-pit-of-success) with
reproducible notebooks - in particular, managing dependencies.

Notebooks are much like one-off Python scripts and therefore do not benefit
from the same dependency management as packages. Being a "good steward" of
notebooks in this context requires discipline (due to the manual nature of
virtual environments) and knowledge of Python packaging - a somewhat
unreasonable expectation for domain experts who are focused on solving
problems, not software engineering.

You will often find a "getting started" guide in the wild like this:

```sh
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt # or just pip install pandas numpy, etc
jupyter lab
```

Four lines of code, where a few things can go wrong. _What version of Python?_
_What package version(s)?_ _What if we forget to activate the virtual
environment?_

The gold standard for a "getting started" guide is a **single command** (i.e,
no guide).

```sh
<magic tool> run notebook.ipynb
```

However, this gold standard has long been out of reach for Jupyter notebooks.
Why?

First, **virtual environments are a leaky abstraction** and deeply ingrained in
the Python psyche: _create_, _activate_, _install_, _run_. Their historical
"cost" has forced us to treat them as entities that must be managed explicitly.
In fact, an entire ecosystem of tooling and best practices are oriented around
supporting long-lived environments, rather than something more ephemeral. End
users separately _create_ and then _mutate_ virtual environments with low-level
tools like `pip`. The manual nature and overhead of these steps encourages
sharing environments across projects.

Second, **only Python packages could historically specify their dependencies**.
Lots of data science code lives in notebooks, not packages, and there has not
been a way to specify dependencies for standalone scripts without external
files (e.g., `requirements.txt`).

*Aligning of the stars*

Two key ideas have changed my perspective on this problem and inspired **juv**:

- **Virtual environments are now "cheap"**. If you'd asked me a year ago, I
would have said virtual environments were a necessary evil.
[uv](https://peps.python.org/pep-0723/) is such a departure from the status quo
that it forces us to rethink best practices. Environments are now created
faster than JupyterLab starts - why keep them around at all?

- **PEP 723**. [Inline script metadata](https://peps.python.org/pep-0723/)
introduces a standard way to specify dependencies in standalone Python scripts.
A single file can now contain everything needed to run it, without relying on
external files like `requirements.txt` or `pyproject.toml`. 

So, what if:

- _Environments were disposable by default?_
- _Notebooks could specify their own dependencies?_

This is the vision of **juv**

> [!NOTE]
> Dependency management is just one challenge for notebook reproducibility
> (non-linear execution being another). **juv** aims to solve this specific
> pain point for the existing ecosystem. I'm personally excited for initiatives
> that [rethink notebooks](https://marimo.io/blog/lessons-learned) from the
> ground up and make a tool like **juv** obsolete.

## How

[PEP 723 (inline script metadata)](https://peps.python.org/pep-0723) allows
specifying dependencies as comments within Python scripts, enabling
self-contained, reproducible execution. This feature could significantly
improve reproducibility in the data science ecosystem, since many analyses are
shared as standalone code (not packages). However, _a lot_ of data science code
lives in notebooks (`.ipynb` files), not Python scripts (`.py` files).

**juv** bridges this gap by:

- Extending PEP 723-style metadata support from `uv` to Jupyter notebooks
- Launching Jupyter sessions for various notebook front ends (e.g., JupyterLab, Notebook, NbClassic) with the specified dependencies

It's a simple Python script that parses the notebook and starts a Jupyter
session with the specified dependencies (piggybacking on `uv`'s existing
functionality).

## Alternatives

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
