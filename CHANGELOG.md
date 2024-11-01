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
