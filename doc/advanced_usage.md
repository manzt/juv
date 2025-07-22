---
title: Advanced Usage
---

# Advanced Usage

This guide covers some of the more advanced features of `juv`, including environment synchronization, timestamping, and the powerful `run` command.

## Environment Synchronization with `juv venv` and `juv sync`

While `juv` excels at creating ephemeral environments, you can also create persistent virtual environments for use with IDEs or other tools.

### `juv venv`

The `juv venv` command creates a dedicated virtual environment from a notebook's dependencies.

```bash
# Create a .venv directory
juv venv --from my_notebook.ipynb
```

By default, this includes `ipykernel` so you can use it as a Jupyter kernel. You can exclude it with `--no-kernel`.

### `juv sync`

The `juv sync` command synchronizes an existing virtual environment with a notebook's dependencies. This is useful for keeping your IDE's environment up-to-date.

```bash
# Sync the environment in the ./.venv directory
juv sync my_notebook.ipynb

# Sync a different environment
juv sync my_notebook.ipynb --target /path/to/my/env

# Sync the currently active environment
juv sync my_notebook.ipynb --active
```

## Reproducible Timestamps with `juv stamp`

The `juv stamp` command adds a timestamp to your notebook's metadata. This timestamp is used by `uv` to resolve dependencies as they were on that date, ensuring bit-for-bit reproducibility.

```bash
# Stamp with the current time
juv stamp my_notebook.ipynb

# Stamp with a specific date
juv stamp my_notebook.ipynb --date 2023-01-01

# Stamp with a specific RFC 3339 timestamp
juv stamp my_notebook.ipynb --timestamp 2023-01-01T00:00:00Z

# Stamp with the timestamp of the latest git commit
juv stamp my_notebook.ipynb --latest

# Clear the timestamp
juv stamp my_notebook.ipynb --clear
```

## The `run` Command in Detail

The `juv run` command is highly flexible. Here are some of its more advanced options.

### Running Different Jupyter Frontends

You can easily switch between Jupyter frontends using the `--jupyter` flag or the `JUV_JUPYTER` environment variable.

```bash
# Use the classic notebook interface
juv run my_notebook.ipynb --jupyter notebook

# Set the default to nbclassic
export JUV_JUPYTER=nbclassic
juv run my_notebook.ipynb
```

### Adding Temporary Dependencies

The `--with` flag allows you to add dependencies for a single session without permanently adding them to the notebook's metadata.

```bash
juv run my_notebook.ipynb --with "polars" "seaborn"
```

## Editing Notebooks as Markdown with `juv edit`

The `juv edit` command allows you to open a notebook's content in your default text editor as a markdown file. This can be a more convenient way to edit text-heavy notebooks.

```bash
# Open the notebook in your $EDITOR
juv edit my_notebook.ipynb

# Specify an editor
juv edit my_notebook.ipynb --editor vim
```

When you save and close the editor, `juv` will convert the markdown back into a notebook file.
