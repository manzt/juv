from __future__ import annotations

import os
import subprocess
import typing
from contextlib import suppress
from dataclasses import dataclass

import jupytext
import tomlkit
from whenever import Date, OffsetDateTime, SystemDateTime, ZonedDateTime

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


def parse_timestamp(date_str: str) -> OffsetDateTime:
    with suppress(ValueError):
        return OffsetDateTime.parse_common_iso(date_str)

    try:
        return OffsetDateTime.parse_rfc3339(date_str)
    except ValueError as err:
        msg = f"'{date_str}' could not be parsed as a valid timestamp."
        raise ValueError(msg) from err


def parse_date(date_str: str) -> OffsetDateTime:
    """Parse a common ISO 8601 date string (using the system's local timezone).

    Defaults to midnight in the local timezone.
    """
    try:
        date = Date.parse_common_iso(date_str).add(days=1)
    except ValueError as err:
        msg = f"'{date_str}' could not be parsed as a valid date."
        raise ValueError(msg) from err

    if "JUV_TZ" in os.environ:
        # used in tests
        dt = ZonedDateTime(date.year, date.month, date.day, tz=os.environ["JUV_TZ"])
    else:
        dt = SystemDateTime(date.year, date.month, date.day)

    return dt.to_fixed_offset()


def get_git_timestamp(rev: str) -> OffsetDateTime:
    """Get the ISO 8601 timestamp of a Git revision."""
    ts = subprocess.check_output(  # noqa: S603
        ["git", "show", "-s", "--format=%cI", rev],  # noqa: S607
        text=True,
    )
    return OffsetDateTime.parse_rfc3339(ts.strip())


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


def stamp(  # noqa: PLR0913
    path: Path,
    *,
    timestamp: str | None,
    latest: bool,
    rev: str | None,
    clear: bool,
    date: str | None,
) -> Action:
    """Update the 'uv.tool.exclude-newer' metadata in a script or notebook."""
    # Determine the timestamp to use
    action = None
    if clear:
        dt = None
    elif latest:
        dt = get_git_timestamp("HEAD")
    elif rev:
        dt = get_git_timestamp(rev)
    elif timestamp:
        dt = parse_timestamp(timestamp)
    elif date:
        dt = parse_date(date)
    else:
        # Default to the current time
        dt = SystemDateTime.now().to_fixed_offset()

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

    script, action = update_inline_metadata(path.read_text(encoding="utf-8"), dt)
    path.write_text(script)
    return action
