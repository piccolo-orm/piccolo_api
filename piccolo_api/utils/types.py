"""
Utils for extracting information from complex, nested types.
"""

from __future__ import annotations

import typing as t

try:
    # Python 3.10 and above
    from types import UnionType  # type: ignore
except ImportError:

    class UnionType:  # type: ignore
        ...


def get_type(type_: t.Type) -> t.Type:
    """
    Extract the inner type from an optional if necessary, otherwise return
    the type as is.

    For example::

        >>> get_type(Optional[int])
        int

        >>> get_type(int | None)
        int

        >>> get_type(int)
        int

        >>> _get_type(list[str])
        list[str]

    """
    origin = t.get_origin(type_)

    # Note: even if `t.Optional` is passed in, the origin is still a
    # `t.Union` or `UnionType` depending on the Python version.
    if any(origin is i for i in (t.Union, UnionType)):
        union_args = t.get_args(type_)

        NoneType = type(None)

        if len(union_args) == 2 and NoneType in union_args:
            return [i for i in union_args if i is not NoneType][0]

    return type_


__all__ = ("get_type",)
