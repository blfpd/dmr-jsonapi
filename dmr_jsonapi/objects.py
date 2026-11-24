"""
Typed models for the objects that JSON:API defines.

They are all :class:`typing.TypedDict` types, so they work with any
serializer that ``django-modern-rest`` supports.
"""

from typing import Any, Generic, NotRequired, TypeAlias

from typing_extensions import TypedDict, TypeVar

#: Free-form non-standard meta information.
Meta: TypeAlias = dict[str, Any]


class LinkObject(TypedDict):
    """A link that carries some extra information, not just an url."""

    href: str
    rel: NotRequired[str]
    describedby: NotRequired[str | dict[str, Any]]
    title: NotRequired[str]
    type: NotRequired[str]
    hreflang: NotRequired[str | list[str]]
    meta: NotRequired[Meta]


#: A link is either an url string or a link object.
Link: TypeAlias = str | LinkObject

#: Named links, ``None`` is used for the links that are not available.
Links: TypeAlias = dict[str, Link | None]


class JsonApiObject(TypedDict):
    """Top level ``jsonapi`` object that describes server's implementation."""

    version: NotRequired[str]
    ext: NotRequired[list[str]]
    profile: NotRequired[list[str]]
    meta: NotRequired[Meta]


class ResourceIdentifier(TypedDict):
    """Identifies a resource without describing it."""

    type: str
    id: str
    lid: NotRequired[str]
    meta: NotRequired[Meta]


class Relationship(TypedDict):
    """
    Relationship of a resource.

    Specification requires at least one of ``links``, ``data``, or ``meta``.
    ``data`` is a single identifier for to-one relationships, a list of them
    for to-many relationships, and ``None`` for empty to-one relationships.
    """

    links: NotRequired[Links]
    data: NotRequired[ResourceIdentifier | list[ResourceIdentifier] | None]
    meta: NotRequired[Meta]


_AttributesT = TypeVar('_AttributesT', default=dict[str, Any])


class ResourceObject(TypedDict, Generic[_AttributesT]):
    """
    A resource, which is the main thing that JSON:API documents carry.

    Define your own ``TypedDict`` for the attributes
    and pass it as a type argument.
    """

    type: str
    id: str
    attributes: NotRequired[_AttributesT]
    relationships: NotRequired[dict[str, Relationship]]
    links: NotRequired[Links]
    meta: NotRequired[Meta]


class NewResourceObject(TypedDict, Generic[_AttributesT]):
    """
    A resource that a client wants to create.

    Unlike :class:`ResourceObject`, ``id`` is optional.
    Servers can accept client-generated ids or generate their own.
    """

    type: str
    id: NotRequired[str]
    lid: NotRequired[str]
    attributes: NotRequired[_AttributesT]
    relationships: NotRequired[dict[str, Relationship]]
    meta: NotRequired[Meta]


#: Resources that are related to the primary data, but are not a part of it.
IncludedResources: TypeAlias = list[ResourceObject[Any]]


class DocumentEnvelope(TypedDict):
    """
    Members that top level documents have in common, except for ``data``.

    The best way to describe your documents is to subclass this type
    and to add ``data`` with a concrete type:

    .. code:: python

        >>> from dmr_jsonapi.objects import DocumentEnvelope, ResourceObject

        >>> class UserAttributes(TypedDict):
        ...     name: str

        >>> class UserDocument(DocumentEnvelope):
        ...     data: ResourceObject[UserAttributes]

    Why? Schema generators name all specializations of a generic
    ``TypedDict`` the same way. So, ``Document[A]`` and ``Document[B]``
    would clash in your OpenAPI schema when used as top level types.
    And python can't substitute type arguments when you subclass
    a specialized generic ``TypedDict``, validation would silently be lost.
    """

    included: NotRequired[IncludedResources]
    links: NotRequired[Links]
    meta: NotRequired[Meta]
    jsonapi: NotRequired[JsonApiObject]


_DataT = TypeVar('_DataT')


class Document(DocumentEnvelope, Generic[_DataT]):
    """
    Top level object of a successful response or of a request.

    ``data`` is a resource, a list of resources,
    a resource identifier (or a list of them), or ``None``.

    It is a handy type for annotating things that build documents,
    like :func:`dmr_jsonapi.builders.document`.
    It is compatible with the documents that subclass
    :class:`DocumentEnvelope`. But prefer to use your own documents
    as response and request models, see the note there.
    """

    data: _DataT


class ErrorSource(TypedDict):
    """
    Points to the place that caused the error.

    Specification only allows one of these to be used at once.
    """

    pointer: NotRequired[str]
    parameter: NotRequired[str]
    header: NotRequired[str]


class ErrorLinks(TypedDict):
    """Links of an error object."""

    about: NotRequired[Link]
    type: NotRequired[Link]


class ErrorObject(TypedDict):
    """A single error, see https://jsonapi.org/format/#error-objects."""

    id: NotRequired[str]
    links: NotRequired[ErrorLinks]
    status: NotRequired[str]
    code: NotRequired[str]
    title: NotRequired[str]
    detail: NotRequired[str]
    source: NotRequired[ErrorSource]
    meta: NotRequired[Meta]


class ErrorDocument(TypedDict):
    """Top level object of an unsuccessful response."""

    errors: list[ErrorObject]
    links: NotRequired[Links]
    meta: NotRequired[Meta]
    jsonapi: NotRequired[JsonApiObject]
