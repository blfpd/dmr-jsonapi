"""Helpers to build JSON:API documents from your data."""

import functools
import math
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from django.http import HttpRequest
from typing_extensions import TypeVar

from dmr_jsonapi._members import with_members
from dmr_jsonapi.constants import JSON_API_VERSION
from dmr_jsonapi.objects import (
    Document,
    Links,
    Meta,
    Relationship,
    ResourceIdentifier,
    ResourceObject,
)

_AttributesT = TypeVar('_AttributesT')
_DataT = TypeVar('_DataT')


def resource_identifier(
    resource_type: str,
    resource_id: str | int | UUID,
    *,
    meta: Meta | None = None,
) -> ResourceIdentifier:
    """
    Build a resource identifier.

    The specification requires ids to be strings, so we convert them.
    """
    identifier: ResourceIdentifier = {
        'type': resource_type,
        'id': str(resource_id),
    }
    return with_members(identifier, {'meta': meta})


def resource_object(  # noqa: WPS211
    resource_type: str,
    resource_id: str | int | UUID,
    attributes: _AttributesT | None = None,
    *,
    relationships: dict[str, Relationship] | None = None,
    links: Links | None = None,
    meta: Meta | None = None,
) -> ResourceObject[_AttributesT]:
    """
    Build a resource object.

    Members that are not passed are not included.
    """
    resource: ResourceObject[_AttributesT] = {
        'type': resource_type,
        'id': str(resource_id),
    }
    return with_members(
        resource,
        {
            'attributes': attributes,
            'relationships': relationships,
            'links': links,
            'meta': meta,
        },
    )


def relationship_to_one(
    identifier: ResourceIdentifier | None,
    *,
    links: Links | None = None,
    meta: Meta | None = None,
) -> Relationship:
    """Build a to-one relationship, ``None`` means that it is empty."""
    relationship: Relationship = {'data': identifier}
    return with_members(relationship, {'links': links, 'meta': meta})


def relationship_to_many(
    identifiers: Iterable[ResourceIdentifier],
    *,
    links: Links | None = None,
    meta: Meta | None = None,
) -> Relationship:
    """Build a to-many relationship."""
    relationship: Relationship = {'data': list(identifiers)}
    return with_members(relationship, {'links': links, 'meta': meta})


def document(  # noqa: WPS211
    data: _DataT,
    *,
    included: list[ResourceObject[Any]] | None = None,
    links: Links | None = None,
    meta: Meta | None = None,
    jsonapi: bool = False,
) -> Document[_DataT]:
    """
    Build a top level document.

    Pass ``jsonapi=True`` to include the ``jsonapi`` member
    with the version of the specification that we implement.
    """
    top_level: Document[_DataT] = {'data': data}
    return with_members(
        top_level,
        {
            'included': included,
            'links': links,
            'meta': meta,
            'jsonapi': {'version': JSON_API_VERSION} if jsonapi else None,
        },
    )


def pagination_links(  # noqa: WPS211
    request: HttpRequest,
    *,
    number: int,
    size: int,
    total: int,
    number_param: str = 'page[number]',
    size_param: str = 'page[size]',
) -> Links:
    """
    Build ``self``, ``first``, ``last``, ``prev``, and ``next`` links.

    Works with page-based pagination, other query parameters
    of the *request* are kept as they are.

    Args:
        request: Current request, urls are built from it.
        number: Number of the current page, starts with ``1``.
        size: Size of one page.
        total: Total number of items in the collection.
        number_param: Name of the query parameter with a page number.
        size_param: Name of the query parameter with a page size.

    """
    if number < 1 or size < 1 or total < 0:
        raise ValueError(
            'Page number and size must be positive, total must not be negative',
        )
    last = max(math.ceil(total / size), 1)
    build_url = functools.partial(
        _build_page_url,
        request,
        size=size,
        number_param=number_param,
        size_param=size_param,
    )
    return {
        'self': build_url(number),
        'first': build_url(1),
        'last': build_url(last),
        'prev': build_url(number - 1) if number > 1 else None,
        'next': build_url(number + 1) if number < last else None,
    }


def _build_page_url(
    request: HttpRequest,
    number: int,
    *,
    size: int,
    number_param: str,
    size_param: str,
) -> str:
    query = request.GET.copy()
    query[number_param] = str(number)
    query[size_param] = str(size)
    return request.build_absolute_uri(f'{request.path}?{query.urlencode()}')
