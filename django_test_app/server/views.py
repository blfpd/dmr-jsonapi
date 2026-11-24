from http import HTTPStatus
from typing import ClassVar, Final, NotRequired

from django.http import HttpRequest
from dmr import Body, Path, ResponseSpec, modify
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.plugins.pydantic import PydanticSerializer
from typing_extensions import TypedDict

from dmr_jsonapi import JsonApiController, JsonApiError
from dmr_jsonapi.builders import (
    document,
    pagination_links,
    relationship_to_one,
    resource_identifier,
    resource_object,
)
from dmr_jsonapi.errors import error_object
from dmr_jsonapi.objects import (
    DocumentEnvelope,
    ErrorDocument,
    NewResourceObject,
    ResourceObject,
)

_RESOURCE_TYPE: Final = 'articles'
_PAGE_SIZE: Final = 2


class ArticleAttributes(TypedDict):
    """Attributes of an article."""

    title: str
    body: NotRequired[str]


class ArticlePath(TypedDict):
    """Path parameters of a single article."""

    article_id: int


_ArticleResource = ResourceObject[ArticleAttributes]


class ArticleDocument(DocumentEnvelope):
    """Document with a single article."""

    data: _ArticleResource


class ArticlesDocument(DocumentEnvelope):
    """Document with a collection of articles."""

    data: list[_ArticleResource]


class NewArticleDocument(DocumentEnvelope):
    """Document that is used to create an article."""

    data: NewResourceObject[ArticleAttributes]


_NOT_FOUND: Final = ResponseSpec(
    ErrorDocument,
    status_code=HTTPStatus.NOT_FOUND,
)
_CONFLICT: Final = ResponseSpec(
    ErrorDocument,
    status_code=HTTPStatus.CONFLICT,
)

#: In-memory storage, we don't need a database to test JSON:API.
ARTICLES: Final[dict[int, ArticleAttributes]] = {}


def _to_resource(
    article_id: int,
    attributes: ArticleAttributes,
) -> _ArticleResource:
    return resource_object(
        _RESOURCE_TYPE,
        article_id,
        attributes,
        relationships={
            'author': relationship_to_one(resource_identifier('people', 1)),
        },
        links={'self': f'/api/articles/{article_id}/'},
    )


def _create(parsed_body: NewArticleDocument) -> ArticleDocument:
    new_resource = parsed_body['data']
    attributes = new_resource.get('attributes')
    if attributes is None:
        raise JsonApiError(
            error_object(
                'Attributes are required',
                code='attributes_required',
                source={'pointer': '/data/attributes'},
            ),
            status_code=HTTPStatus.CONFLICT,
        )
    article_id = len(ARTICLES) + 1
    ARTICLES[article_id] = attributes
    return document(_to_resource(article_id, attributes), jsonapi=True)


def _get(article_id: int) -> ArticleDocument:
    attributes = ARTICLES.get(article_id)
    if attributes is None:
        raise JsonApiError(
            error_object(
                f'Article {article_id} does not exist',
                code='article_not_found',
                title='Article not found',
            ),
            status_code=HTTPStatus.NOT_FOUND,
        )
    return document(_to_resource(article_id, attributes))


def _list(request: HttpRequest) -> ArticlesDocument:
    number = int(request.GET.get('page[number]', '1'))
    start = (number - 1) * _PAGE_SIZE
    ids = sorted(ARTICLES)[start : start + _PAGE_SIZE]
    return document(
        [_to_resource(article_id, ARTICLES[article_id]) for article_id in ids],
        links=pagination_links(
            request,
            number=number,
            size=_PAGE_SIZE,
            total=len(ARTICLES),
        ),
        meta={'total': len(ARTICLES)},
    )


class ArticlesController(JsonApiController[PydanticSerializer]):
    """Sync collection endpoints that use ``pydantic``."""

    responses: ClassVar = (_CONFLICT,)

    def get(self) -> ArticlesDocument:
        return _list(self.request)

    @modify(status_code=HTTPStatus.CREATED)
    def post(self, parsed_body: Body[NewArticleDocument]) -> ArticleDocument:
        return _create(parsed_body)


class ArticleController(JsonApiController[PydanticSerializer]):
    """Sync single resource endpoint that uses ``pydantic``."""

    responses: ClassVar = (_NOT_FOUND,)

    def get(self, parsed_path: Path[ArticlePath]) -> ArticleDocument:
        return _get(parsed_path['article_id'])


class AsyncArticlesController(JsonApiController[MsgspecSerializer]):
    """Async collection endpoints that use ``msgspec``."""

    responses: ClassVar = (_CONFLICT,)

    async def get(self) -> ArticlesDocument:
        return _list(self.request)

    @modify(status_code=HTTPStatus.CREATED)
    async def post(
        self,
        parsed_body: Body[NewArticleDocument],
    ) -> ArticleDocument:
        return _create(parsed_body)


class AsyncArticleController(JsonApiController[MsgspecSerializer]):
    """Async single resource endpoint that uses ``msgspec``."""

    responses: ClassVar = (_NOT_FOUND,)

    async def get(self, parsed_path: Path[ArticlePath]) -> ArticleDocument:
        return _get(parsed_path['article_id'])
