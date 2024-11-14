## 0.2.24

### Enhancements

- Add support for regular Python script in `juv add` ([#51](https://github.com/manzt/juv/pull/51))
- Add `--pin` flag for `juv add` ([#51](https://github.com/manzt/juv/pull/51))

### Notes

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


## 0.2.23

### Enhancements

- Add `juv stamp` for time-based dependency resolution pinning ([#50](https://github.com/manzt/juv/pull/50))

### Notes

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
