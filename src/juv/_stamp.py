from __future__ import annotations

import subprocess
import sys
import typing
from contextlib import suppress
from dataclasses import dataclass

import jupytext
import rich
import tomlkit
from whenever import Date, OffsetDateTime, SystemDateTime

from ._nbutils import write_ipynb
from ._pep723 import (
    extract_inline_meta,
    includes_inline_metadata,
    parse_inline_script_metadata,
)

if typing.TYPE_CHECKING:
    from pathlib import Path


@dataclass
class DeleteAction:
    previous: str | None


@dataclass
class CreateAction:
    value: str


@dataclass
class UpdateAction:
    previous: str
    value: str


Action = typing.Union[DeleteAction, CreateAction, UpdateAction]


def parse_offset_datetime(date_str: str) -> OffsetDateTime:
    """Parse a string into an `OffsetDateTime` object.

    Tries to parse ISO 8601-compliant timestamps first.

    If parsing fails, tries to parse an RFC 3339 timestamp.

    If parsing fails, falls back to parsing a common ISO 8601 date string
    (using the system's local timezone). If the date is successfully parsed
    without a time component, it defaults to midnight in the local timezone.

    This tries to follow the same logic as `uv run --exclude-newer=<value>`.
    """
    with suppress(ValueError):
        return OffsetDateTime.parse_common_iso(date_str)

    with suppress(ValueError) as err:
        return OffsetDateTime.parse_rfc3339(date_str)

    try:
        date = Date.parse_common_iso(date_str).add(days=1)
    except ValueError as err:
        msg = f"'{date_str}' could not be parsed as a valid date."
        raise ValueError(msg) from err

    return SystemDateTime(date.year, date.month, date.day).to_fixed_offset()


def get_git_timestamp(rev: str) -> OffsetDateTime:
    """Get the ISO 8601 timestamp of a Git revision."""
    ts = subprocess.check_output(  # noqa: S603
        ["git", "show", "-s", "--format=%cI", rev],  # noqa: S607
        text=True,
    )
    return OffsetDateTime.parse_rfc3339(ts.strip())


def resolve_offset_datetime(
    *, time: str | None, rev: str | None, latest: bool, clear: bool
) -> OffsetDateTime | None:
    if clear:
        return None
    if latest:
        return get_git_timestamp("HEAD")
    if rev:
        return get_git_timestamp(rev)
    if time:
        return parse_offset_datetime(time)
    # Default to the current time
    return SystemDateTime.now().to_fixed_offset()


def update_inline_metadata(
    script: str, dt: OffsetDateTime | None
) -> tuple[str, Action]:
    meta_comment, _ = extract_inline_meta(script)

    if meta_comment is None:
        msg = "No PEP 723 metadata block found."
        raise ValueError(msg)

    toml = parse_inline_script_metadata(meta_comment)

    if toml is None:
        msg = "No TOML metadata found in the PEP 723 metadata block."
        raise ValueError(msg)

    meta = tomlkit.parse(toml)
    tool = meta.get("tool")
    if tool is None:
        tool = meta["tool"] = tomlkit.table()

    uv = tool.get("uv")
    if uv is None:
        uv = tool["uv"] = tomlkit.table()

    if dt is None:
        action = DeleteAction(previous=uv.pop("exclude-newer", None))
        if not uv:
            tool.pop("uv")
            if not tool:
                meta.pop("tool")
    else:
        previous = uv.get("exclude-newer", None)
        current = dt.format_common_iso()
        uv["exclude-newer"] = current
        action = (
            CreateAction(value=current)
            if previous is None
            else UpdateAction(previous=previous, value=current)
        )

    new_toml = tomlkit.dumps(meta).strip()
    new_meta_comment = "\n".join(
        [
            "# /// script",
            *[f"# {line}" if line else "#" for line in new_toml.splitlines()],
            "# ///",
        ]
    )
    return script.replace(meta_comment, new_meta_comment), action


def stamp(
    path: Path, *, time: str | None, latest: bool, rev: str | None, clear: bool
) -> Action:
    """Update the 'uv.tool.exclude-newer' metadata in a script or notebook."""
    dt = resolve_offset_datetime(time=time, rev=rev, latest=latest, clear=clear)
    action = None

    if path.suffix == ".ipynb":
        nb = jupytext.read(path)

        for cell in filter(lambda c: c.cell_type == "code", nb.cells):
            source = "".join(cell.source)
            if includes_inline_metadata(source):
                source, action = update_inline_metadata(source, dt)
                cell.source = source.splitlines(keepends=True)
                break

        if action is None:
            msg = "No PEP 723 metadata block found."
            raise ValueError(msg)

        write_ipynb(nb, path)
        return action

    script, action = update_inline_metadata(path.read_text(), dt)
    path.write_text(script)
    return action
