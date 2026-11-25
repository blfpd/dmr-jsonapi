from http import HTTPStatus
from typing import Any

import msgspec
import pytest
from django.conf import LazySettings
from dmr.errors import ErrorType
from dmr.exceptions import (
    InternalServerError,
    NotAcceptableError,
    ValidationError,
)
from inline_snapshot import snapshot

from dmr_jsonapi.errors import (
    JsonApiError,
    error_object,
    format_error,
    source_from_loc,
    with_status,
)


def test_error_object_empty() -> None:
    """Ensure that nothing is included unless it is passed."""
    assert error_object() == {}


def test_error_object_full() -> None:
    """Ensure that all members can be set, ``status`` becomes a string."""
    assert error_object(
        'detail',
        status_code=HTTPStatus.NOT_FOUND,
        code='missing',
        title='Missing',
        error_id='abc',
        links={'about': '/errors/missing/'},
        source={'pointer': '/data'},
        meta={'a': 1},
    ) == snapshot({
        'id': 'abc',
        'links': {'about': '/errors/missing/'},
        'status': '404',
        'code': 'missing',
        'title': 'Missing',
        'detail': 'detail',
        'source': {'pointer': '/data'},
        'meta': {'a': 1},
    })


def test_with_status() -> None:
    """Ensure that status is only set when it is missing."""
    original = {'errors': [{'detail': 'a'}, {'detail': 'b', 'status': '400'}]}
    assert with_status(original, HTTPStatus.CONFLICT) == snapshot({
        'errors': [
            {'detail': 'a', 'status': '409'},
            {'detail': 'b', 'status': '400'},
        ],
    })
    # No mutation:
    assert original['errors'][0] == {'detail': 'a'}


@pytest.mark.parametrize('raw_data', [None, 'text', {'data': []}, [1]])
def test_with_status_other_data(raw_data: Any) -> None:
    """Ensure that things that are not errors are not touched."""
    assert with_status(raw_data, HTTPStatus.CONFLICT) is raw_data


def test_json_api_error() -> None:
    """Ensure that exception stores a ready to use document."""
    exc = JsonApiError(
        error_object('first'),
        error_object('second', status_code=HTTPStatus.BAD_REQUEST),
        status_code=HTTPStatus.CONFLICT,
        headers={'X-Test': '1'},
    )
    assert exc.status_code == HTTPStatus.CONFLICT
    assert exc.headers == {'X-Test': '1'}
    assert exc.raw_data == snapshot({
        'errors': [
            {'detail': 'first', 'status': '409'},
            {'detail': 'second', 'status': '400'},
        ],
    })


def test_json_api_error_empty() -> None:
    """Ensure that at least one error is required."""
    with pytest.raises(ValueError, match='At least one'):
        JsonApiError(status_code=HTTPStatus.CONFLICT)


@pytest.mark.parametrize(
    ('loc', 'expected'),
    [
        ([], False),
        (['parsed_body'], {'pointer': ''}),
        (
            ['parsed_body', 'data', 'attributes', 0, 'a/b', 'c~d'],
            {'pointer': '/data/attributes/0/a~1b/c~0d'},
        ),
        (['parsed_query', 'page[size]'], {'parameter': 'page[size]'}),
        (['parsed_query'], False),
        (['parsed_headers', 'X-Token'], {'header': 'X-Token'}),
        (['parsed_headers'], False),
        (['parsed_cookies', 'session'], False),
        (['parsed_path', 'user_id'], False),
    ],
)
def test_source_from_loc(
    loc: list[str | int],
    expected: Any,
) -> None:
    """Ensure that locations are converted to proper error sources."""
    assert source_from_loc(loc) == expected


def test_format_error_str() -> None:
    """Ensure that regular messages are supported."""
    assert format_error(
        'Something',
        loc=['parsed_query', 'q'],
        error_type=ErrorType.user_msg,
    ) == snapshot({
        'errors': [
            {
                'code': 'user_msg',
                'detail': 'Something',
                'source': {'parameter': 'q'},
            },
        ],
    })
    assert format_error('Plain') == {'errors': [{'detail': 'Plain'}]}


def test_format_error_unknown_loc() -> None:
    """Ensure that we do not lose locations that can't be sources."""
    assert format_error('Wrong', loc='parsed_cookies') == snapshot({
        'errors': [
            {
                'detail': 'Wrong',
                'meta': {'loc': ['parsed_cookies']},
            },
        ],
    })


def test_format_validation_error() -> None:
    """Ensure that validation errors are converted one by one."""
    exc = ValidationError(
        [
            {'msg': 'bad', 'type': 'value_error', 'loc': ['parsed_body', 'a']},
            {'msg': 'worse'},
        ],
        status_code=HTTPStatus.BAD_REQUEST,
    )
    assert format_error(exc) == snapshot({
        'errors': [
            {
                'status': '400',
                'code': 'value_error',
                'detail': 'bad',
                'source': {'pointer': '/a'},
            },
            {'status': '400', 'detail': 'worse'},
        ],
    })


@pytest.mark.parametrize(
    ('message', 'expected'),
    [
        (
            'Expected `str`, got `int` - at `$.parsed_body.data.name`',
            {
                'detail': 'Expected `str`, got `int`',
                'source': {'pointer': '/data/name'},
            },
        ),
        (
            'Oops - at `$.parsed_body.data[1].items[0]`',
            {'detail': 'Oops', 'source': {'pointer': '/data/1/items/0'}},
        ),
        (
            'Oops - at `$.parsed_query.page`',
            {'detail': 'Oops', 'source': {'parameter': 'page'}},
        ),
        # Field names can contain brackets, even with dots inside:
        (
            'Expected `int`, got `str` - at `$.parsed_query.page[size]`',
            {
                'detail': 'Expected `int`, got `str`',
                'source': {'parameter': 'page[size]'},
            },
        ),
        (
            'Oops - at `$.parsed_query.filter[a.b]`',
            {'detail': 'Oops', 'source': {'parameter': 'filter[a.b]'}},
        ),
        (
            'Oops - at `$.parsed_body.meta[x][y][2].z`',
            {'detail': 'Oops', 'source': {'pointer': '/meta[x][y]/2/z'}},
        ),
        # Unknown fields are only in the message:
        (
            'Object contains unknown field `sort` - at `$.parsed_query`',
            {
                'detail': 'Object contains unknown field `sort`',
                'source': {'parameter': 'sort'},
            },
        ),
        (
            'Object contains unknown field `a/b` - at `$.parsed_body.data`',
            {
                'detail': 'Object contains unknown field `a/b`',
                'source': {'pointer': '/data/a~1b'},
            },
        ),
        # We don't know keys of dicts, so we point to the dict itself:
        (
            'Expected `int`, got `str` - at `$.parsed_body.meta[...][0]`',
            {
                'detail': 'Expected `int`, got `str`',
                'source': {'pointer': '/meta'},
            },
        ),
        (
            'Object contains unknown field `x` - at `$.parsed_body[...]`',
            {
                'detail': 'Object contains unknown field `x`',
                'source': {'pointer': ''},
            },
        ),
        # Paths that we don't understand stay in the message:
        (
            'Oops - at `$.parsed_body.data]`',
            {'detail': 'Oops - at `$.parsed_body.data]`'},
        ),
        (
            'Oops - at `$.parsed_cookies.name`',
            {
                'detail': 'Oops',
                'meta': {'loc': ['parsed_cookies', 'name']},
            },
        ),
        # The root is not a location that we can point to:
        ('Oops - at `$`', {'detail': 'Oops'}),
        # Not a message of `msgspec`:
        ('Missing - at `x`', {'detail': 'Missing - at `x`'}),
    ],
)
def test_format_msgspec_location(
    message: str,
    expected: dict[str, Any],
) -> None:
    """Ensure that we can use locations that ``msgspec`` puts in messages."""
    exc = ValidationError([{'msg': message}])
    assert format_error(exc) == {
        'errors': [{'status': '422', **expected}],
    }


class _Query(
    msgspec.Struct,
    forbid_unknown_fields=True,
    rename={'page_size': 'page[size]'},
):
    page_size: int = 10


class _Request(msgspec.Struct):
    parsed_query: _Query


@pytest.mark.parametrize(
    ('parsed_query', 'expected'),
    [
        ({'page[size]': 'x'}, {'parameter': 'page[size]'}),
        ({'sort': 'x'}, {'parameter': 'sort'}),
    ],
)
def test_format_real_msgspec_error(
    parsed_query: dict[str, Any],
    expected: dict[str, str],
) -> None:
    """Ensure that we understand messages that ``msgspec`` really makes."""
    with pytest.raises(msgspec.ValidationError) as exc_info:
        msgspec.convert({'parsed_query': parsed_query}, _Request)
    exc = ValidationError([{'msg': str(exc_info.value)}])
    assert format_error(exc)['errors'][0].get('source') == expected


def test_format_other_exceptions() -> None:
    """Ensure that other exceptions of ``dmr`` are supported."""
    assert format_error(NotAcceptableError('Nope')) == snapshot({
        'errors': [
            {'status': '406', 'code': 'value_error', 'detail': 'Nope'},
        ],
    })


def test_format_internal_error(settings: LazySettings) -> None:
    """Ensure that internal errors are hidden unless we are debugging."""
    settings.DEBUG = False
    assert format_error(InternalServerError('Secret')) == snapshot({
        'errors': [{'status': '500', 'detail': 'Internal server error'}],
    })
    settings.DEBUG = True
    assert format_error(InternalServerError('Secret')) == snapshot({
        'errors': [{'status': '500', 'detail': 'Secret'}],
    })
