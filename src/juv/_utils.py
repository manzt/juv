from __future__ import annotations

import typing

T = typing.TypeVar("T")


def find(cb: typing.Callable[[T], bool], items: list[T]) -> T | None:
    """Find the first item in a list that satisfies a condition.

    Parameters
    ----------
    cb : Callable[[T], bool]
        The condition to satisfy.
    items : list[T]
        The list to search.

    Returns
    -------
    T | None
        The first item that satisfies the condition, or None if no item does.

    """
    return next((item for item in items if cb(item)), None)
