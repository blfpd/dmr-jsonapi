import re
from collections.abc import Set
from itertools import takewhile
from typing import Final

from dmr_jsonapi.constants import JSON_API_CONTENT_TYPE, JSON_API_MEDIA_PARAMS

# Splits by a separator that is not inside of a quoted string:
_COMMA: Final = re.compile(r',(?=(?:[^"]*"[^"]*")*[^"]*$)')
_SEMICOLON: Final = re.compile(r';(?=(?:[^"]*"[^"]*")*[^"]*$)')


def is_accept_unsatisfiable(
    accept: str | None,
    allowed_params: Set[str] = JSON_API_MEDIA_PARAMS,
) -> bool:
    """
    Tell whether ``Accept`` header can't be satisfied by a JSON:API server.

    The specification says that if ``Accept`` has the JSON:API media type
    and all of its instances are modified with media type parameters
    (other than ``ext`` and ``profile``), a server must return ``406``.

    Other media types and the headers that don't mention JSON:API at all
    are not our business, so they are never reported here.
    """
    if accept is None or ';' not in accept:
        return False  # fast path, there are no parameters

    instances = 0
    for media_range in _COMMA.split(accept.lower()):
        media_type, *parts = (
            part.strip() for part in _SEMICOLON.split(media_range)
        )
        if media_type != JSON_API_CONTENT_TYPE:
            continue
        instances += 1
        if _param_names(parts) <= allowed_params:
            return False
    return instances > 0


def _param_names(parts: list[str]) -> set[str]:
    names = (part.partition('=')[0].strip() for part in parts)
    # Parameters after `q` are not media type parameters:
    return set(takewhile(lambda name: name != 'q', names))
