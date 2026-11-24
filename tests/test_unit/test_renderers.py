from datetime import UTC, datetime
from decimal import Decimal

import pytest
from dmr.parsers import JsonParser
from dmr.renderers import JsonRenderer

from dmr_jsonapi.constants import JSON_API_CONTENT_TYPE
from dmr_jsonapi.parsers import JsonApiParser
from dmr_jsonapi.renderers import JsonApiRenderer


def test_renderer_content_type() -> None:
    """Ensure that we render the right media type by default."""
    assert JsonApiRenderer().content_type == JSON_API_CONTENT_TYPE
    assert JsonApiRenderer('application/x').content_type == 'application/x'
    assert isinstance(JsonApiRenderer(), JsonRenderer)


def test_render() -> None:
    """Ensure that documents are rendered as compact json."""
    assert (
        JsonApiRenderer().render({'data': None, 'meta': {'a': [1]}}, str)
        == b'{"data":null,"meta":{"a":[1]}}'
    )


@pytest.mark.parametrize(
    ('to_render', 'expected'),
    [
        (datetime(2026, 11, 24, 10, tzinfo=UTC), b'"2026-11-24T10:00:00Z"'),
        (Decimal('1.5'), b'"1.5"'),
    ],
)
def test_render_special_types(to_render: object, expected: bytes) -> None:
    """Ensure that the json backend handles types that django developers use."""
    assert JsonApiRenderer().render(to_render, str) == expected


def test_render_hook() -> None:
    """Ensure that the hook is used for unknown types."""
    assert (
        JsonApiRenderer().render({'data': object}, lambda _: 'obj')
        == b'{"data":"obj"}'
    )


def test_validation_parser() -> None:
    """Ensure that the parser can read what the renderer wrote."""
    renderer = JsonApiRenderer()
    parser = renderer.validation_parser
    # It must not check media types, because there is no request:
    assert isinstance(parser, JsonParser)
    assert not isinstance(parser, JsonApiParser)
    assert parser.content_type == JSON_API_CONTENT_TYPE
