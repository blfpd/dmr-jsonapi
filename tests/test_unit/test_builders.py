import uuid
from typing import Final

import pytest
from django.test import RequestFactory
from inline_snapshot import snapshot

from dmr_jsonapi.builders import (
    document,
    pagination_links,
    relationship_to_many,
    relationship_to_one,
    resource_identifier,
    resource_object,
)

_IDENTIFIER: Final = resource_identifier('people', 1)


def test_resource_identifier() -> None:
    """Ensure that ids are always strings."""
    assert snapshot({'type': 'people', 'id': '1'}) == _IDENTIFIER
    unique = uuid.UUID(int=1)
    assert resource_identifier('people', unique, meta={'a': 1}) == {
        'type': 'people',
        'id': str(unique),
        'meta': {'a': 1},
    }


def test_resource_object_minimal() -> None:
    """Ensure that only required members are included by default."""
    assert resource_object('users', 1) == snapshot({'type': 'users', 'id': '1'})


def test_resource_object_full() -> None:
    """Ensure that all members are included when they are passed."""
    assert resource_object(
        'users',
        'abc',
        {'name': 'sobolevn'},
        relationships={'friend': relationship_to_one(None)},
        links={'self': '/users/abc/'},
        meta={'extra': True},
    ) == snapshot({
        'type': 'users',
        'id': 'abc',
        'attributes': {'name': 'sobolevn'},
        'relationships': {'friend': {'data': None}},
        'links': {'self': '/users/abc/'},
        'meta': {'extra': True},
    })


def test_to_one() -> None:
    """Ensure that to-one relationships can be built."""
    assert relationship_to_one(_IDENTIFIER) == {'data': _IDENTIFIER}
    assert relationship_to_one(
        _IDENTIFIER,
        links={'related': '/people/1/'},
        meta={'a': 1},
    ) == snapshot({
        'data': {'type': 'people', 'id': '1'},
        'links': {'related': '/people/1/'},
        'meta': {'a': 1},
    })


def test_to_many() -> None:
    """Ensure that to-many relationships can be built from any iterable."""
    assert relationship_to_many(iter([_IDENTIFIER])) == {'data': [_IDENTIFIER]}
    assert relationship_to_many(
        [],
        links={'self': '/x/'},
        meta={'a': 1},
    ) == snapshot({
        'data': [],
        'links': {'self': '/x/'},
        'meta': {'a': 1},
    })


def test_document() -> None:
    """Ensure that documents include only what is passed."""
    assert document(None) == {'data': None}
    assert document(
        [],
        included=[],
        links={'self': '/'},
        meta={'a': 1},
        jsonapi=True,
    ) == snapshot({
        'data': [],
        'included': [],
        'links': {'self': '/'},
        'meta': {'a': 1},
        'jsonapi': {'version': '1.1'},
    })


def test_pagination_middle() -> None:
    """Ensure that all links exist in the middle of the collection."""
    request = RequestFactory().get(
        '/articles/',
        {'filter[a]': 'b', 'page[number]': '2', 'page[size]': '10'},
    )
    assert pagination_links(request, number=2, size=10, total=35) == snapshot({
        'self': 'http://testserver/articles/?filter%5Ba%5D=b&page%5Bnumber%5D=2&page%5Bsize%5D=10',
        'first': 'http://testserver/articles/?filter%5Ba%5D=b&page%5Bnumber%5D=1&page%5Bsize%5D=10',
        'last': 'http://testserver/articles/?filter%5Ba%5D=b&page%5Bnumber%5D=4&page%5Bsize%5D=10',
        'prev': 'http://testserver/articles/?filter%5Ba%5D=b&page%5Bnumber%5D=1&page%5Bsize%5D=10',
        'next': 'http://testserver/articles/?filter%5Ba%5D=b&page%5Bnumber%5D=3&page%5Bsize%5D=10',
    })


@pytest.mark.parametrize(
    ('number', 'total', 'prev', 'next_'),
    [
        (1, 35, None, 'http://testserver/a/?p=2&s=10'),
        (4, 35, 'http://testserver/a/?p=3&s=10', None),
        (1, 0, None, None),
        (1, 10, None, None),
    ],
)
def test_pagination_edges(
    *,
    number: int,
    total: int,
    prev: str | None,
    next_: str | None,
) -> None:
    """Ensure that ``prev`` and ``next`` are ``None`` on the edges."""
    links = pagination_links(
        RequestFactory().get('/a/'),
        number=number,
        size=10,
        total=total,
        number_param='p',
        size_param='s',
    )
    assert links['prev'] == prev
    assert links['next'] == next_
    assert links['first'] == 'http://testserver/a/?p=1&s=10'


@pytest.mark.parametrize(
    ('number', 'size', 'total'),
    [(0, 10, 1), (1, 0, 1), (1, 10, -1)],
)
def test_pagination_invalid(*, number: int, size: int, total: int) -> None:
    """Ensure that nonsense numbers are not accepted."""
    with pytest.raises(ValueError, match='must be positive'):
        pagination_links(
            RequestFactory().get('/a/'),
            number=number,
            size=size,
            total=total,
        )
