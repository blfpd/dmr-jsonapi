from collections.abc import Iterator

import pytest

# Registers `settings` fixture that cleans `dmr` caches:
from dmr_pytest import settings  # noqa: F401

from dmr_jsonapi.constants import JSON_API_CONTENT_TYPE
from server.views import ARTICLES


@pytest.fixture(autouse=True)
def _clean_articles() -> Iterator[None]:
    """The storage is global, so we must clean it between tests."""
    ARTICLES.clear()
    yield
    ARTICLES.clear()


@pytest.fixture
def jsonapi_headers() -> dict[str, str]:
    """Headers that a valid JSON:API client sends."""
    return {'Accept': JSON_API_CONTENT_TYPE}
