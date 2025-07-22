---
title: API Reference
---

# API Reference

This page provides a detailed reference for `juv`'s command-line interface.

## Global Options

-   `--version`: Show the version and exit.
-   `--help`: Show help text and exit.

## `juv init`

Initialize a new notebook.

-   **Usage**: `juv init [OPTIONS] [FILE]`
-   **Arguments**:
    -   `[FILE]`: The path to the notebook file to create. If not provided, a default name will be used.
-   **Options**:
    -   `--python, -p TEXT`: The Python interpreter to use.
    -   `--with TEXT`: A comma-separated list of packages to add to the new notebook.

## `juv add`

Add dependencies to a notebook.

-   **Usage**: `juv add [OPTIONS] FILE [PACKAGES]...`
-   **Arguments**:
    -   `FILE`: The notebook to modify.
    -   `[PACKAGES]...`: The packages to add.
-   **Options**:
    -   `--requirements, -r TEXT`: Path to a `requirements.txt` file.
    -   `--pin`: Pin the resolved versions in the notebook metadata.

## `juv run`

Launch a notebook in a Jupyter frontend.

-   **Usage**: `juv run [OPTIONS] FILE [JUPYTER_ARGS]...`
-   **Arguments**:
    -   `FILE`: The notebook to run.
    -   `[JUPYTER_ARGS]...`: Arguments to pass to the Jupyter frontend.
-   **Options**:
    -   `--jupyter TEXT`: The Jupyter frontend to use (e.g., `lab`, `notebook`).
    -   `--with TEXT`: Temporary dependencies for this session.
    -   `--python, -p TEXT`: The Python interpreter to use.

## `juv lock`

Create or update a notebook's lockfile.

-   **Usage**: `juv lock [OPTIONS] FILE`
-   **Arguments**:
    -   `FILE`: The notebook to lock.
-   **Options**:
    -   `--clear`: Clear the lockfile.

## `juv venv`

Create a persistent virtual environment from a notebook.

-   **Usage**: `juv venv [OPTIONS] [PATH]`
-   **Arguments**:
    -   `[PATH]`: The path to create the virtual environment at. Defaults to `.venv`.
-   **Options**:
    -   `--from TEXT`: The source notebook.
    -   `--python, -p TEXT`: The Python interpreter to use.
    -   `--no-kernel`: Do not install `ipykernel`.

## `juv sync`

Sync a virtual environment with a notebook's dependencies.

-   **Usage**: `juv sync [OPTIONS] PATH`
-   **Arguments**:
    -   `PATH`: The notebook to sync from.
-   **Options**:
    -   `--target TEXT`: The path to the virtual environment to sync.
    -   `--active`: Sync the active virtual environment.
    -   `--python, -p TEXT`: The Python interpreter to use.
    -   `--no-kernel`: Do not install `ipykernel`.

## `juv stamp`

Stamp a notebook with a reproducible timestamp.

-   **Usage**: `juv stamp [OPTIONS] FILE`
-   **Arguments**:
    -   `FILE`: The notebook to stamp.
-   **Options**:
    -   `--date TEXT`: A date in `YYYY-MM-DD` format.
    -   `--timestamp TEXT`: An RFC 3339 timestamp.
    -   `--rev TEXT`: A git revision.
    -   `--latest`: Use the latest git commit.
    -   `--clear`: Clear the timestamp.

## `juv edit`

Edit a notebook as markdown.

-   **Usage**: `juv edit [OPTIONS] NOTEBOOK`
-   **Arguments**:
    -   `NOTEBOOK`: The notebook to edit.
-   **Options**:
    -   `--editor TEXT`: The editor to use.

## `juv clear`

Clear notebook cell outputs.

-   **Usage**: `juv clear [OPTIONS] [FILES]...`
-   **Arguments**:
    -   `[FILES]...`: The notebook(s) to clear.
-   **Options**:
    -   `--check`: Check if notebooks are cleared without modifying them.

## `juv tree`

Display a notebook's dependency tree.

-   **Usage**: `juv tree FILE`
-   **Arguments**:
    -   `FILE`: The notebook to analyze.

## `juv cat`

Print notebook contents to stdout.

-   **Usage**: `juv cat [OPTIONS] NOTEBOOK`
-   **Arguments**:
    -   `NOTEBOOK`: The notebook to print.
-   **Options**:
    -   `--script`: Print as a Python script.

