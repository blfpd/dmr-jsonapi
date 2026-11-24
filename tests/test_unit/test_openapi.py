import json
from typing import Any

import pytest
from django.urls import get_resolver
from dmr.openapi import build_schema
from dmr.routing import Router

from dmr_jsonapi.constants import JSON_API_CONTENT_TYPE
from server.urls import router


@pytest.fixture(scope='session')
def schema() -> dict[str, Any]:
    """OpenAPI schema of the test project as a simple object."""
    built = build_schema(router)
    return json.loads(json.dumps(built.convert()))  # type: ignore[no-any-return]


def test_schema_uses_media_type(schema: dict[str, Any]) -> None:
    """Ensure that requests and responses use JSON:API media type."""
    operation = schema['paths']['/api/articles/']['post']

    assert list(operation['requestBody']['content']) == [JSON_API_CONTENT_TYPE]
    for status, response in operation['responses'].items():
        assert list(response['content']) == [JSON_API_CONTENT_TYPE], status


def test_schema_describes_errors(schema: dict[str, Any]) -> None:
    """Ensure that errors are described with the JSON:API error document."""
    responses = schema['paths']['/api/articles/']['post']['responses']

    # Added by the renderer, the parser, and the controller:
    assert {'406', '409', '415'} <= set(responses)
    error_schema = responses['409']['content'][JSON_API_CONTENT_TYPE]['schema']
    assert error_schema == {'$ref': '#/components/schemas/ErrorDocument'}
    assert (
        'errors'
        in schema['components']['schemas']['ErrorDocument']['properties']
    )


def test_router_is_a_router() -> None:
    """Sanity check for the test project."""
    assert isinstance(router, Router)
    assert get_resolver().url_patterns
