# Contributing to juv

**juv** welcomes contributions in the form of bug reports, feature requests,
and pull requests. 

For small changes, feel free to open a PR directly. For larger changes, please
open an issue first to discuss the proposed changes.

## Prerequisites

**juv** is a Python package that uses [uv](https://github.com/astral-sh/uv) for
development. Please make sure you have it installed before contributing.

## Development

After cloning the repo, you can run an editable install of **juv** with `uv run`:

```sh
uv run juv
```

Prior to opening a PR, ensure that your code has been auto-formatted and that
it passes both lint and test validation checks.

```sh
uv run ruff format # auto-format code
uv run ruff check  # check lint validation
uv run pytest      # run tests
```

## Release Process

To release a new version of **juv**, run the following:

```sh
uvx --from 'rooster-blue>=0.0.9' rooster release # [--bump major|minor|patch]
uv sync # sync version in lockfile
```

This will bump the version of **juv** and update the CHANGELOG.md. Changelog
entries are based on the commit messages and use GitHub labels to categorize
the release sections.

Then open a PR with the title: `vX.Y.Z`. Once the PR is merged, we will make a
release by manually running the release.yml workflow.
