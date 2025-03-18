## 0.4.0

### Release Notes

This release is considered **breaking** since it sets a minimum bound on `uv`
dependency to v0.6.7 or later. This could potentially affect environments where
both `juv` and `uv` are Python dependencies, and there is an upper bound on the
`uv` version (unlikely).

There are no intentional breaking changes to `juv` commands.

### Enhancements

- Add explicit `juv sync` command ([#84](https://github.com/manzt/juv/pull/84))

### Breaking changes

- Replace `juv venv` internals with `uv sync --script` ([#84](https://github.com/manzt/juv/pull/84))

### Contributors
- [@manzt](https://github.com/manzt)

## 0.3.4

### Bug fixes

- Support stdin `--requirements` with `juv add` ([#83](https://github.com/manzt/juv/pull/83))

### Contributors
- [@manzt](https://github.com/manzt)

## 0.3.3

### Enhancements

- Extend `juv venv` regular python scripts as well ([#82](https://github.com/manzt/juv/pull/82))

Allows for passing a script with inline script metadata to `juv venv`.

```sh
uv init --script foo.py
uv add --script foo.py attrs
juv venv --from=foo.py
# Using CPython 3.13.0
# Creating virtual environment at: .venv
# Activate with: source .venv/bin/activate
# Using Python 3.13.0 environment at: .venv
# Resolved 1 package in 0.62ms
# Installed 1 package in 1ms
# + attrs==25.1.0
```

Useful for quickly creating a `.venv` for a standalone script, which can be used by other tools like text editors or IDEs.

### Contributors
- [@manzt](https://github.com/manzt)

## 0.3.2

### Enhancements

- Add `juv venv` to support exporting explicit notebook environments ([#80](https://github.com/manzt/juv/pull/80))

Some editors and environments are missing the benefits of standalone notebooks because **juv** manages virtual environments transparently within `juv run`. To improve compatibility with other tools (e.g., editors & IDEs), this release adds `juv venv` to *export* a virtual environment with all a notebook's specified dependencies (and `ipykernel`):

```sh
juv venv --from=Untitled.ipynb
# Using CPython 3.13.0
# Creating virtual environment at: .venv
# Activate with: source .venv/bin/activate
```

The resulting environment (i.e., `.venv`) can be selected in an editor like VS Code to run the notebook.

To create a virtual environment with *only* the locked dependencies (i.e., without `ipykernel`), use the `--no-kernel` flag:

```sh
juv venv --from=Untitled.ipynb --no-kernel
```

### Contributors
- [@manzt](https://github.com/manzt)

## 0.3.1

### Enhancements

- Add `--index` and `--default-index` flags to `juv add` ([#76](https://github.com/manzt/juv/pull/76))

### Contributors
- [@manzt](https://github.com/manzt)

## 0.3.0

### Release Notes

This release adds support for generating lockfiles from Jupyter notebooks using
inline metadata, as defined in PEP 723.

By default, notebooks remain unlocked. To lock a notebook, run `juv lock /path/to/notebook.ipynb`,
which generates and embeds a lockfile in the notebook's metadata under the
`"uv.lock"` key. The lockfile is respected and updated automatically when using
`juv run`, `uv add`, or `uv remove`.

Additional commands:

- **`juv export`**: Outputs an alternative lockfile format (requirements.txt
style) to stdout.
- **`uv tree`**: Displays the dependency tree for a script.

Both commands work with notebooks, whether locked or unlocked.

This release is considered **breaking** due to the lockfile support, which
requires a minimum `uv` 0.5.18 and modifies execution.

### Breaking changes

- Upgrade minimum uv to v0.5 ([#63](https://github.com/manzt/juv/pull/63))
- Respect lockfile in `run` ([#67](https://github.com/manzt/juv/pull/67))

### Enhancements

- Add `--clear` flag to `lock` to clear lockfile metadata ([#69](https://github.com/manzt/juv/pull/69))
- Add `export` command ([#70](https://github.com/manzt/juv/pull/70))
- Add `lock` command ([#64](https://github.com/manzt/juv/pull/64))
- Add `tree` command ([#68](https://github.com/manzt/juv/pull/68))
- Sync lockfile during `add` command ([#65](https://github.com/manzt/juv/pull/65))
- Sync lockfile during `remove` command ([#66](https://github.com/manzt/juv/pull/66))

### Bug fixes

- Require at least one package for `add` and `remove` ([#73](https://github.com/manzt/juv/pull/73))
- Support relative paths in the `run` command ([#72](https://github.com/manzt/juv/pull/72))

### Contributors
- [@manzt](https://github.com/manzt)

## 0.2.28

### Release Notes

This release adds `juv remove` to remove packages from a notebook or script.
Dependencies are removed from the PEP-723 inline metadata. The command follows
uv's semantics. See the [uv
docs](https://docs.astral.sh/uv/reference/cli/#uv-remove) for more information.

```sh
uvx juv init
uvx juv add Untitled.ipynb 'numpy>=1.0.0' 'polars' # adds 'numpy>=1.0.0' 'polars'
uvx juv remove Untitled.ipynb numpy # removes 'numpy>=1.0.0'
```

### Other changes

- Add `remove` command ([#59](https://github.com/manzt/juv/pull/59))

### Contributors
- [@manzt](https://github.com/manzt)

## 0.2.27

### Enhancements

- Force UTF-8 encoding when reading/writing text ([#56](https://github.com/manzt/juv/pull/56))

### Bug fixes

- Use TemporaryDirectoryIgnoreErrors in replacement template ([#57](https://github.com/manzt/juv/pull/57))

### Contributors
- [@manzt](https://github.com/manzt)

## 0.2.26

### Enhancements

- Support windows with `juv run` ([#54](https://github.com/manzt/juv/pull/54))

### Contributors
- [@ATL2001](https://github.com/ATL2001)

## 0.2.25

### Enhancements

- Bubble up uv errors from `juv add --pin` ([#52](https://github.com/manzt/juv/pull/52))
- Add `kernelspec` metadata to new notebooks ([#53](https://github.com/manzt/juv/pull/53))

## 0.2.24

### Release Notes

This release adds `--pin` flag to `juv add` to have package specifiers resolved to an exact version at the time of the command, and subsequently pinned in the notebook/script.

```sh
uvx juv init
uvx juv add Untitled.ipynb 'numpy>=1.0.0' 'polars' # adds 'numpy>=1' 'polars'
uvx juv add Untitled.ipynb numpy polars --pin      # adds 'numpy==2.1.3' 'polars==1.13.1'
```

This same behavior can be achieved without juv for regular scripts with a unix pipe:

```sh
echo 'numpy\npolars' | uv pip compile --no-deps - | grep '==' | xargs uv add --script foo.py
```

But alternatively you can use `juv add` for the same thing:

```sh
uv init --script foo.py
uvx juv add foo.py numpy polars --pin
```

### Enhancements

- Add support for regular Python script in `juv add` ([#51](https://github.com/manzt/juv/pull/51))
- Add `--pin` flag for `juv add` ([#51](https://github.com/manzt/juv/pull/51))

## 0.2.23

### Release Notes

`uv` supports time-based dependency resolution via [`exclude-newer`](https://simonwillison.net/2024/May/10/uv-pip-install-exclude-newer/),
allowing packages to be resolved as they existed at a specific moment in time.

This feature greatly enhances the reproducibility of one-off scripts and notebooks without needing a lockfile.
However, `exclude-newer` requires a full RFC 3339 timestamp (e.g., 2020-03-05T00:00:00-05:00), which can be tedious to manage manually.

This release introduces `juv stamp`, a command that provides a high-level,
ergonomic API for pinning and unpinning various relevant timestamps in **both
standalone Python scripts and Jupyter notebooks**:

```sh
# Stamp a notebook
juv init foo.ipynb
juv stamp foo.ipynb

# Stamp with a specific time
juv stamp foo.ipynb --time "2020-03-05T00:00:00-05:00"
juv stamp foo.ipynb --date 2022-01-03

# Use Git revisions
juv stamp foo.ipynb --rev e20c99
juv stamp foo.ipynb --latest

# Clear the pinned timestamp
juv stamp foo.ipynb --clear
```

```sh
# For Python scripts
uv init --script foo.py
uv add --script foo.py polars anywidget
uvx juv stamp foo.py
```

### Enhancements

- Add `juv stamp` for time-based dependency resolution pinning ([#50](https://github.com/manzt/juv/pull/50))

## 0.2.22

### Enhancements

- Clear widgets metadata in `clear` ([#49](https://github.com/manzt/juv/pull/49))

## 0.2.21

### Enhancements

- Upgrade uv to v0.5.0 ([#47](https://github.com/manzt/juv/pull/47))

## 0.2.20

### Enhancements

- Add `--pager` flag for `juv cat` ([#45](https://github.com/manzt/juv/pull/45))

### Other changes

- Refactor environment vars to also accept flags ([#46](https://github.com/manzt/juv/pull/46))

## 0.2.19

### Enhancements

- Add `--check` flag for `juv clear` ([#44](https://github.com/manzt/juv/pull/44))

### Bug fixes

- Use managed temp dir for `JUPYTER_DATA_DIR` ([#43](https://github.com/manzt/juv/pull/43))

## 0.2.18

### Bug fixes

- Change directories prior to running uv ([#41](https://github.com/manzt/juv/pull/41))

## 0.2.17

### Release Notes

This release adds some nice cli flags to `juv add` for configuring various kinds of dependency sources:

Include "extra" dependency groups with `--extra`:

```sh
juv add Untitled.ipynb --extra dev anywidget # adds `anywidget[dev]`
```

Treat a local source as editable with `--editable`:

```sh
juv add Untitled.ipynb --editable ./path/to/packages
```

Add a git source at a specific revision (i.e., commit), tag, or branch:

```sh
juv add Untitled.ipynb git+https://github.com/encode/httpx --tag 0.27.0
juv add Untitled.ipynb git+https://github.com/encode/httpx --branch master
juv add Untitled.ipynb git+https://github.com/encode/httpx --rev 326b9431c761e1ef1e00b9f760d1f654c8db48c6
```

### Enhancements

- Support `--editable` sources for `add` ([#39](https://github.com/manzt/juv/pull/39))
- Support `add --extra` ([#38](https://github.com/manzt/juv/pull/38))
- Support git sources with `add` ([#40](https://github.com/manzt/juv/pull/40))
- Add help information for command line flags ([#40](https://github.com/manzt/juv/pull/40))

## 0.2.16

### Enhancements

- Refactor `run` to use isolated scripts ([#37](https://github.com/manzt/juv/pull/37))
- Respect inline requires-python for python request ([#36](https://github.com/manzt/juv/pull/36))

## 0.2.15

### Enhancements

- Support forwarding flags to underlying Jupyter front end ([#35](https://github.com/manzt/juv/pull/35))

## 0.2.14

### Enhancements

- Replace `cat --format` with `cat --script` ([#33](https://github.com/manzt/juv/pull/33))
- Include `id` metadata for markdown editing for better diffing ([#34](https://github.com/manzt/juv/pull/34))

### Bug fixes

- Fix so that cells are diffed by longest ([#32](https://github.com/manzt/juv/pull/32))

## 0.2.13

### Enhancements

- Add `cat` command ([#28](https://github.com/manzt/juv/pull/28))
- Require editing in markdown for better diffs ([#31](https://github.com/manzt/juv/pull/31))

## 0.2.12

### Bug fixes

- Strip content for editor ([#27](https://github.com/manzt/juv/pull/27))

## 0.2.11

### Enhancements

- Add `exec` command ([#23](https://github.com/manzt/juv/pull/23))
- Hide notebook metadata in `edit` ([#26](https://github.com/manzt/juv/pull/26))

### Other changes

- Add `edit` command for quick editing in default editor ([#24](https://github.com/manzt/juv/pull/24))
- More consistent clear message ([#25](https://github.com/manzt/juv/pull/25))

## 0.2.10

### Enhancements

- Allow specifying directories for `clear` ([#22](https://github.com/manzt/juv/pull/22))

## 0.2.9

### Enhancements

- Add `clear` command ([#20](https://github.com/manzt/juv/pull/20))

## 0.2.8

### Enhancements

- Add `--output-format` flag for `version` command ([#18](https://github.com/manzt/juv/pull/18))

## 0.2.7

### Enhancements

- Add new empty cell to new notebooks ([#15](https://github.com/manzt/juv/pull/15))

## 0.2.6

### Other changes

- Add PyPI shield to README ([#14](https://github.com/manzt/juv/pull/14))

## 0.2.5

### Breaking changes

- Switch to click CLI ([#6](https://github.com/manzt/juv/pull/6))

### Enhancements

- Add `--with` flag to init ([#8](https://github.com/manzt/juv/pull/8))
- Add `add`/`init` commands ([#2](https://github.com/manzt/juv/pull/2))
- Add managed run mode via `JUV_RUN_MODE=managed` env ([#9](https://github.com/manzt/juv/pull/9))
- Make nicer CLI output text ([#5](https://github.com/manzt/juv/pull/5))
- Use jupytext for creating notebooks ([#1](https://github.com/manzt/juv/pull/1))

### Bug fixes
- Support Python 3.8 and test on ubuntu ([#11](https://github.com/manzt/juv/pull/11))
