"""Errors in JSON:API format, see https://jsonapi.org/format/#errors."""

import re
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import Any, Final, Literal, TypeGuard

from dmr.cookies import NewCookie
from dmr.errors import ErrorDetail, ErrorType
from dmr.errors import format_error as dmr_format_error
from dmr.response import APIError

from dmr_jsonapi._members import with_members
from dmr_jsonapi.objects import (
    ErrorDocument,
    ErrorLinks,
    ErrorObject,
    ErrorSource,
    Meta,
)

# `msgspec` does not provide a location, but it adds it to the message:
# Expected `str`, got `int` - at `$.parsed_body.data.attributes[0].name`
_MSGSPEC_MESSAGE: Final = re.compile(r'^(?P<msg>.*) - at `\$(?P<path>.*)`$')
# Field names can contain brackets, like `page[size]` or `filter[a.b]`.
# `[0]` is always an index, `[...]` is a key of a dict that `msgspec`
# does not name.
_PATH_PART: Final = re.compile(
    r'\.(?P<key>[^.\[\]]+(?:\[(?!\d+\]|\.\.\.\])[^\[\]]*\])*)'
    r'|\[(?P<index>\d+)\]'
    r'|(?P<dict_key>\[\.\.\.\])',
)
# The unknown field is only in the message, the location is its parent:
# Object contains unknown field `sort` - at `$.parsed_query`
_UNKNOWN_FIELD: Final = re.compile(
    r'^Object contains unknown field `(?P<field>.*)`$',
)


def error_object(  # noqa: WPS211
    detail: str | None = None,
    *,
    status_code: HTTPStatus | None = None,
    code: str | None = None,
    title: str | None = None,
    error_id: str | None = None,
    links: ErrorLinks | None = None,
    source: ErrorSource | None = None,
    meta: Meta | None = None,
) -> ErrorObject:
    """
    Build a single error object.

    Only the passed members are included.
    ``status`` is a string in JSON:API, we convert *status_code* for you.
    """
    error: ErrorObject = {}
    return with_members(
        error,
        {
            'id': error_id,
            'links': links,
            'status': None if status_code is None else str(status_code.value),
            'code': code,
            'title': title,
            'detail': detail,
            'source': source,
            'meta': meta,
        },
    )


def with_status(raw_data: Any, status_code: HTTPStatus) -> Any:
    """
    Fill the missing ``status`` of errors in a document.

    It is how we make sure that ``status`` always matches the status code
    of the response. Existing ``status`` values are kept as they are.
    Anything that does not look like an error document is returned as is.
    """
    if not _is_error_document(raw_data):
        return raw_data
    status = str(status_code.value)
    return {
        **raw_data,
        'errors': [
            error if 'status' in error else {'status': status, **error}
            for error in raw_data['errors']
        ],
    }


def _is_error_document(raw_data: Any) -> TypeGuard[ErrorDocument]:
    return isinstance(raw_data, dict) and 'errors' in raw_data


class JsonApiError(APIError[ErrorDocument]):
    """
    Raise it anywhere in your API to return errors in JSON:API format.

    It is a subclass of :class:`dmr.response.APIError`.
    Build errors with :func:`error_object`:

    .. code:: python

        >>> from http import HTTPStatus
        >>> from dmr_jsonapi.errors import JsonApiError, error_object

        >>> raise JsonApiError(
        ...     error_object('User does not exist', code='no_user'),
        ...     status_code=HTTPStatus.NOT_FOUND,
        ... )
        Traceback (most recent call last):
          ...
        dmr_jsonapi.errors.JsonApiError

    Several errors can be returned at once, ``status`` of each of them
    is set to *status_code* when it is missing.
    """

    def __init__(
        self,
        *errors: ErrorObject,
        status_code: HTTPStatus,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
    ) -> None:
        """Create an error from error objects, at least one is required."""
        if not errors:
            raise ValueError('At least one error object is required')
        super().__init__(
            with_status({'errors': list(errors)}, status_code),
            status_code=status_code,
            headers=headers,
            cookies=cookies,
        )


def source_from_loc(
    loc: Sequence[str | int],
) -> ErrorSource | Literal[False]:
    """
    Convert ``dmr`` error location to the error source.

    Returns ``False`` when location can't be represented as a source.
    """
    if not loc:
        return False
    component, *path = loc
    if component == 'parsed_body':
        return {'pointer': _to_pointer(path)}
    if component == 'parsed_query' and path:
        return {'parameter': str(path[0])}
    if component == 'parsed_headers' and path:
        return {'header': str(path[0])}
    return False


def format_error(
    error: str | Exception,
    *,
    loc: str | list[str | int] | None = None,
    error_type: str | ErrorType | None = None,
) -> ErrorDocument:
    """
    Convert any error to a JSON:API error document.

    It has the same signature as :func:`dmr.errors.format_error`,
    and it handles the same set of errors.
    """
    status_code: HTTPStatus | None = getattr(error, 'status_code', None)
    default = dmr_format_error(error, loc=loc, error_type=error_type)
    return {
        'errors': [
            _convert_detail(detail, status_code) for detail in default['detail']
        ],
    }


def _convert_detail(
    detail: ErrorDetail,
    status_code: HTTPStatus | None,
) -> ErrorObject:
    message = detail['msg']
    loc: list[str | int] | None = detail.get('loc')
    if loc is None:
        message, loc = _msgspec_location(message)

    source = source_from_loc(loc) if loc else False
    return error_object(
        message,
        status_code=status_code,
        code=detail.get('type'),
        source=source or None,
        # We don't want to lose information about locations
        # that cannot be represented as a source:
        meta={'loc': loc} if loc and not source else None,
    )


def _msgspec_location(message: str) -> tuple[str, list[str | int] | None]:
    match = _MSGSPEC_MESSAGE.match(message)
    if match is None:
        return message, None
    loc, is_complete = _parse_msgspec_path(match.group('path'))
    if loc is None:
        # Better to keep the location in the message than to lose it:
        return message, None
    unknown = _UNKNOWN_FIELD.match(match.group('msg'))
    if unknown and is_complete:
        loc.append(unknown.group('field'))
    return match.group('msg'), loc


def _parse_msgspec_path(path: str) -> tuple[list[str | int] | None, bool]:
    """
    Parse a path, it is not complete when it contains a key of a dict.

    We stop at the dict itself then, since we can't point any deeper.
    """
    loc: list[str | int] = []
    position = 0
    while position < len(path):
        part = _PATH_PART.match(path, position)
        if part is None:
            return None, False
        if part.group('dict_key'):
            return loc, False
        key, index = part.group('key', 'index')
        loc.append(key if index is None else int(index))
        position = part.end()
    return loc, True


def _to_pointer(path: Sequence[str | int]) -> str:
    # See RFC 6901, `~` must be escaped first:
    return ''.join(f'/{_escape_pointer_part(part)}' for part in path)


def _escape_pointer_part(part: str | int) -> str:
    return str(part).replace('~', '~0').replace('/', '~1')
