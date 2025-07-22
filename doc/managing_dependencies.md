# Managing Dependencies

`juv` provides several ways to manage your notebook's dependencies, ensuring your projects are reproducible and easy to share.

## Adding Dependencies Permanently

The most common way to add a dependency is with the `juv add` command. This will add the package to your notebook's metadata, so it will be included every time you run `juv run`.

```bash
juv add my_notebook.ipynb pandas
```

## Adding Temporary Dependencies at Launch

If you want to use a package for a single session without adding it to your notebook's permanent dependencies, you can use the `--with` flag when you run your notebook.

```bash
juv run my_notebook.ipynb --with "matplotlib"
```

This is useful for one-off experiments or for using tools like visualization libraries that aren't part of your core analysis.

## Installing Dependencies During a Live Session

What if you're already in a Jupyter session started by `juv run` and you realize you need a new package?

Since `juv` creates an isolated environment for each session, you can't use `juv add` from another terminal to modify the live environment. However, you can use `pip` or `uv pip` directly within a notebook cell to install packages into the current running kernel.

### Using `pip`

You can execute shell commands in a notebook cell by prepending them with an exclamation mark (`!`).

```python
# In a notebook cell
!pip install beautifulsoup4
```

### Using `uv`

If you want to take advantage of `uv`'s speed, you can use `uv pip install`:

```python
# In a notebook cell
!uv pip install beautifulsoup4
```

After running the install command, you can import and use the package in subsequent cells.

**Important Note**: Packages installed this way are temporary and will only be available for the current session. If you want to make the dependency permanent, you should stop the current session and use `juv add` from your terminal. This ensures that your notebook's metadata accurately reflects its dependencies, which is key for reproducibility.
