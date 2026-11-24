from collections.abc import Mapping
from typing import Any, TypeVar, cast

_BaseT = TypeVar('_BaseT', bound=Mapping[str, Any])


def with_members(base: _BaseT, optional: Mapping[str, Any]) -> _BaseT:
    """
    Add optional members to the *base*, but only the ones that were passed.

    Returns a new object of the same ``TypedDict`` type as *base*.
    Never use it for members that can legitimately be ``None``,
    like ``data`` of a document, they must be a part of the *base*.
    """
    return cast(
        _BaseT,
        {
            **base,
            **{
                member_name: member
                for member_name, member in optional.items()
                if member is not None
            },
        },
    )
