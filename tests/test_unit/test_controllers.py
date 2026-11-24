import json
from http import HTTPStatus
from typing import Any, Final

import pytest
from django.http import HttpResponse
from django.urls import reverse
from dmr.test import DMRAsyncClient, DMRClient
from inline_snapshot import snapshot

from dmr_jsonapi.constants import JSON_API_CONTENT_TYPE

_PREFIXES: Final = pytest.mark.parametrize(
    'prefix',
    ['articles', 'async_articles'],
    ids=['sync-pydantic', 'async-msgspec'],
)


def _body(response: HttpResponse) -> Any:
    assert response['Content-Type'] == JSON_API_CONTENT_TYPE
    return json.loads(response.content)


def _new_article(**attributes: str) -> dict[str, Any]:
    return {'data': {'type': 'articles', 'attributes': attributes}}


async def _call(
    client: DMRClient | DMRAsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> HttpResponse:
    """Test both sync and async controllers in a single way."""
    response = getattr(client, method)(url, **kwargs)
    if isinstance(client, DMRAsyncClient):
        return await response  # type: ignore[no-any-return]
    return response  # type: ignore[no-any-return]


@pytest.fixture(params=['sync', 'async'])
def kind(request: pytest.FixtureRequest) -> str:
    """Kind of controllers that we test."""
    return str(request.param)


@pytest.fixture
def client(
    kind: str,
    dmr_client: DMRClient,
    dmr_async_client: DMRAsyncClient,
) -> DMRClient | DMRAsyncClient:
    """Client of the same kind as controllers."""
    return dmr_client if kind == 'sync' else dmr_async_client


@pytest.fixture
def list_url(kind: str) -> str:
    """Url of the collection."""
    return reverse('api:articles' if kind == 'sync' else 'api:async_articles')


def _detail_url(kind: str, article_id: int) -> str:
    name = 'article' if kind == 'sync' else 'async_article'
    return reverse(f'api:{name}', kwargs={'article_id': article_id})


async def _create(
    client: DMRClient | DMRAsyncClient,
    url: str,
    **attributes: str,
) -> HttpResponse:
    return await _call(
        client,
        'post',
        url,
        data=_new_article(**attributes),
        headers={'Content-Type': JSON_API_CONTENT_TYPE},
    )


async def test_create_and_get(
    client: DMRClient | DMRAsyncClient,
    kind: str,
    list_url: str,
    jsonapi_headers: dict[str, str],
) -> None:
    """Ensure that we can create a resource and read it back."""
    created = await _create(client, list_url, title='Hello', body='World')

    assert created.status_code == HTTPStatus.CREATED
    assert _body(created) == snapshot({
        'data': {
            'type': 'articles',
            'id': '1',
            'attributes': {'title': 'Hello', 'body': 'World'},
            'relationships': {
                'author': {'data': {'type': 'people', 'id': '1'}},
            },
            'links': {'self': '/api/articles/1/'},
        },
        'jsonapi': {'version': '1.1'},
    })

    fetched = await _call(
        client,
        'get',
        _detail_url(kind, 1),
        headers=jsonapi_headers,
    )
    assert fetched.status_code == HTTPStatus.OK
    assert _body(fetched)['data']['attributes']['title'] == 'Hello'


async def test_default_accept(
    client: DMRClient | DMRAsyncClient,
    list_url: str,
) -> None:
    """Ensure that clients without ``Accept`` get JSON:API."""
    response = await _call(client, 'get', list_url)

    assert response.status_code == HTTPStatus.OK
    assert not _body(response)['data']


async def test_pagination(
    client: DMRClient | DMRAsyncClient,
    list_url: str,
    jsonapi_headers: dict[str, str],
) -> None:
    """Ensure that collections have links and meta."""
    for title in ('a', 'b', 'c'):
        await _create(client, list_url, title=title)

    first = _body(
        await _call(client, 'get', list_url, headers=jsonapi_headers),
    )
    assert [article['id'] for article in first['data']] == ['1', '2']
    assert first['meta'] == {'total': 3}
    assert first['links']['prev'] is None
    assert first['links']['next'].endswith(
        'page%5Bnumber%5D=2&page%5Bsize%5D=2',
    )

    second = _body(
        await _call(
            client,
            'get',
            list_url,
            data={'page[number]': '2'},
            headers=jsonapi_headers,
        ),
    )
    assert [article['id'] for article in second['data']] == ['3']
    assert second['links']['next'] is None


async def test_not_found(
    client: DMRClient | DMRAsyncClient,
    kind: str,
    jsonapi_headers: dict[str, str],
) -> None:
    """Ensure that raised JSON:API errors are rendered."""
    response = await _call(
        client,
        'get',
        _detail_url(kind, 404),
        headers=jsonapi_headers,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert _body(response) == snapshot({
        'errors': [
            {
                'status': '404',
                'code': 'article_not_found',
                'title': 'Article not found',
                'detail': 'Article 404 does not exist',
            },
        ],
    })


async def test_conflict(
    client: DMRClient | DMRAsyncClient,
    list_url: str,
) -> None:
    """Ensure that errors can point to the document."""
    response = await _call(
        client,
        'post',
        list_url,
        data={'data': {'type': 'articles'}},
        headers={'Content-Type': JSON_API_CONTENT_TYPE},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert _body(response)['errors'][0]['source'] == {
        'pointer': '/data/attributes',
    }


async def test_validation_error(
    client: DMRClient | DMRAsyncClient,
    list_url: str,
) -> None:
    """Ensure that validation errors of ``dmr`` have JSON:API format."""
    response = await _call(
        client,
        'post',
        list_url,
        data={'data': {'type': 'articles', 'attributes': {'title': 1}}},
        headers={'Content-Type': JSON_API_CONTENT_TYPE},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    errors = _body(response)['errors']
    assert errors[0]['status'] == '400'
    assert errors[0]['source'] == {'pointer': '/data/attributes/title'}


async def test_wrong_content_type(
    client: DMRClient | DMRAsyncClient,
    list_url: str,
) -> None:
    """Ensure that other media types are not accepted."""
    response = await _call(
        client,
        'post',
        list_url,
        data=_new_article(title='a'),
        headers={'Content-Type': 'application/json'},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert 'application/vnd.api+json' in _body(response)['errors'][0]['detail']


async def test_content_type_params(
    client: DMRClient | DMRAsyncClient,
    list_url: str,
) -> None:
    """Ensure that media type parameters in requests result in ``415``."""
    response = await _call(
        client,
        'post',
        list_url,
        data=_new_article(title='a'),
        headers={'Content-Type': f'{JSON_API_CONTENT_TYPE}; charset=utf-8'},
    )

    assert response.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE
    assert _body(response)['errors'][0]['source'] == {'header': 'Content-Type'}


async def test_accept_params(
    client: DMRClient | DMRAsyncClient,
    list_url: str,
) -> None:
    """Ensure that media type parameters in ``Accept`` result in ``406``."""
    response = await _call(
        client,
        'get',
        list_url,
        headers={'Accept': f'{JSON_API_CONTENT_TYPE}; charset=utf-8'},
    )

    assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
    assert _body(response)['errors'][0]['status'] == '406'


async def test_accept_ext(
    client: DMRClient | DMRAsyncClient,
    list_url: str,
) -> None:
    """Ensure that ``ext`` and ``profile`` parameters are fine."""
    response = await _call(
        client,
        'get',
        list_url,
        headers={'Accept': f'{JSON_API_CONTENT_TYPE}; ext="https://x.org/e"'},
    )

    assert response.status_code == HTTPStatus.OK


async def test_method_not_allowed(
    client: DMRClient | DMRAsyncClient,
    list_url: str,
) -> None:
    """Ensure that ``405`` is also a JSON:API document."""
    response = await _call(client, 'delete', list_url)

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response['Allow'] == 'GET, POST'
    assert _body(response) == snapshot({
        'errors': [
            {
                'code': 'not_allowed',
                'detail': "Method 'DELETE' is not allowed, allowed: ['GET', 'POST']",
                'status': '405',
            },
        ],
    })
