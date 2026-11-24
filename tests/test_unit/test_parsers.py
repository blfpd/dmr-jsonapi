from http import HTTPStatus
from typing import Any

import pytest
from django.http import HttpRequest
from django.test import RequestFactory
from dmr.exceptions import DataParsingError
from inline_snapshot import snapshot

from dmr_jsonapi.constants import JSON_API_CONTENT_TYPE
from dmr_jsonapi.errors import JsonApiError
from dmr_jsonapi.parsers import JsonApiParser


def _request(content_type: str) -> HttpRequest:
    return RequestFactory().post('/', data=b'{}', content_type=content_type)


def test_parser_content_type() -> None:
    """Ensure that we parse the right media type by default."""
    assert JsonApiParser().content_type == JSON_API_CONTENT_TYPE
    assert JsonApiParser('application/x').content_type == 'application/x'


@pytest.mark.parametrize(
    'content_type',
    [
        JSON_API_CONTENT_TYPE,
        f'{JSON_API_CONTENT_TYPE}; ext="https://example.com/ext"',
        f'{JSON_API_CONTENT_TYPE}; profile="https://example.com/p"',
        f'{JSON_API_CONTENT_TYPE}; ext="a"; profile="b"',
    ],
)
def test_parse_allowed(content_type: str) -> None:
    """Ensure that valid media types are parsed."""
    assert JsonApiParser().parse(
        b'{"data": null}',
        request=_request(content_type),
        model=Any,
    ) == {'data': None}


def test_parse_empty_body() -> None:
    """Ensure that empty bodies are treated the same way ``dmr`` does it."""
    assert (
        JsonApiParser().parse(
            b'',
            request=_request(JSON_API_CONTENT_TYPE),
            model=Any,
        )
        is None
    )


def test_parse_invalid_json() -> None:
    """Ensure that broken bodies are not parsed."""
    with pytest.raises(DataParsingError):
        JsonApiParser().parse(
            b'{',
            request=_request(JSON_API_CONTENT_TYPE),
            model=Any,
        )


def test_parse_no_content_type() -> None:
    """Ensure that requests without params work, like the ones in tests."""
    request = HttpRequest()
    assert request.content_params is None
    assert JsonApiParser().parse(b'[]', request=request, model=Any) == []


@pytest.mark.parametrize(
    'content_type',
    [
        f'{JSON_API_CONTENT_TYPE}; charset=utf-8',
        f'{JSON_API_CONTENT_TYPE}; ext="a"; version=2',
    ],
)
def test_parse_unsupported_params(content_type: str) -> None:
    """Ensure that unsupported parameters result in ``415``."""
    with pytest.raises(JsonApiError) as exc_info:
        JsonApiParser().parse(
            b'{}',
            request=_request(content_type),
            model=Any,
        )
    assert exc_info.value.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE
    error = exc_info.value.raw_data['errors'][0]
    assert error.get('source') == {'header': 'Content-Type'}


def test_parse_custom_params() -> None:
    """Ensure that allowed parameters can be changed."""
    request = _request(f'{JSON_API_CONTENT_TYPE}; charset=utf-8')
    parser = JsonApiParser(allowed_params={'charset'})
    assert parser.parse(b'{}', request=request, model=Any) == {}
    with pytest.raises(JsonApiError) as exc_info:
        JsonApiParser(allowed_params=frozenset()).parse(
            b'{}',
            request=request,
            model=Any,
        )
    assert exc_info.value.raw_data == snapshot({
        'errors': [
            {
                'code': 'unsupported_media_type',
                'detail': "Media type parameters ['charset'] are not supported for application/vnd.api+json, only [] can be used",
                'source': {'header': 'Content-Type'},
                'status': '415',
            },
        ],
    })
