# dmr-jsonapi

*[JSON:API](https://jsonapi.org/) support for [django-modern-rest](https://github.com/wemake-services/django-modern-rest).*

[![Tests Result](https://github.com/blfpd/dmr-jsonapi/actions/workflows/test.yml/badge.svg?event=push)](https://github.com/blfpd/dmr-jsonapi/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/dmr-jsonapi.svg)](https://pypi.org/project/dmr-jsonapi/)
[![Supported Python Version](https://img.shields.io/pypi/pyversions/dmr-jsonapi.svg)](https://pypi.org/project/dmr-jsonapi/)
[![Code Style](https://img.shields.io/badge/style-wemake-000000.svg)](https://github.com/wemake-services/wemake-python-styleguide)

## Features

- Parses and renders `application/vnd.api+json`
- Typed models for resources, relationships, links, documents, and errors,
  they work with `pydantic`, `msgspec`, and any other serializer
  that `django-modern-rest` supports
- Every error, including the ones that `django-modern-rest` raises
  by itself, becomes a JSON:API error document with `status`, `code`,
  `detail`, and `source`
- Follows the media type rules of the specification:
  `415` for unsupported `Content-Type` parameters,
  `406` for unsupported `Accept` parameters
- Helpers to build documents and pagination links
- OpenAPI schema with the right media types and error documents
- Fully typed, 100% test coverage, same tools and style as `django-modern-rest`

## Installation

```bash
pip install dmr-jsonapi
```

Works with `django-modern-rest` from `0.15` to `0.17`
and Python 3.11 and newer.

## Quick start

Describe your resource, your document, and use `JsonApiController`
instead of a regular `Controller`:

```python
>>> from typing_extensions import TypedDict

>>> from dmr import Path
>>> from dmr.plugins.pydantic import PydanticSerializer
>>> from dmr_jsonapi import JsonApiController
>>> from dmr_jsonapi.builders import document, resource_object
>>> from dmr_jsonapi.objects import DocumentEnvelope, ResourceObject

>>> class UserAttributes(TypedDict):
...     name: str

>>> class UserPath(TypedDict):
...     user_id: int

>>> class UserDocument(DocumentEnvelope):
...     data: ResourceObject[UserAttributes]

>>> class UserController(JsonApiController[PydanticSerializer]):
...     def get(self, parsed_path: Path[UserPath]) -> UserDocument:
...         attributes: UserAttributes = {'name': 'Zamenhof'}
...         return document(
...             resource_object('users', parsed_path['user_id'], attributes),
...         )

```

Call it like any other controller. The response has the JSON:API media type:

```python
>>> from dmr.test import DMRRequestFactory

>>> request = DMRRequestFactory().get('/users/1/')
>>> response = UserController.as_view()(request, user_id=1)
>>> response.status_code
200
>>> response['Content-Type']
'application/vnd.api+json'
>>> response.content
b'{"data":{"type":"users","id":"1","attributes":{"name":"Zamenhof"}}}'

```

### Name your documents

Define documents by subclassing `DocumentEnvelope` and adding `data`,
like `UserDocument` above. Do not use `Document[ResourceObject[...]]`
as a top level request or response type.
Schema generators name every specialization of a generic `TypedDict`
the same, so two of them clash in your OpenAPI schema.
Python also can't substitute type arguments when you subclass
a specialized generic `TypedDict`, so validation would silently go away.

`Document[...]` is still handy to annotate your own helpers,
the documents that you define this way are compatible with it.

## Errors

All errors that `django-modern-rest` produces (validation, `404`, `406`,
`405`, throttling, authentication, and so on) are rendered as JSON:API errors:

```python
>>> import json

>>> class ArticleController(JsonApiController[PydanticSerializer]):
...     def get(self) -> UserDocument:
...         raise NotImplementedError

>>> request = DMRRequestFactory().delete('/articles/')
>>> response = ArticleController.as_view()(request)
>>> response.status_code
405
>>> json.loads(response.content)['errors'][0]['status']
'405'

```

Validation errors point to the broken place in the request:

```json
{
  "errors": [
    {
      "status": "400",
      "code": "value_error",
      "detail": "Input should be a valid string",
      "source": {"pointer": "/data/attributes/name"}
    }
  ]
}
```

Locations of the body become JSON pointers, locations of query parameters
and headers become `source.parameter` and `source.header`.

To return your own errors, raise `JsonApiError` anywhere in your API:

```python
>>> from http import HTTPStatus
>>> from dmr import ResponseSpec
>>> from dmr_jsonapi import JsonApiError
>>> from dmr_jsonapi.errors import error_object
>>> from dmr_jsonapi.objects import ErrorDocument

>>> class MissingUserController(JsonApiController[PydanticSerializer]):
...     responses = (
...         ResponseSpec(ErrorDocument, status_code=HTTPStatus.NOT_FOUND),
...     )
...
...     def get(self) -> UserDocument:
...         raise JsonApiError(
...             error_object(
...                 'User does not exist',
...                 code='user_not_found',
...                 source={'parameter': 'user_id'},
...             ),
...             status_code=HTTPStatus.NOT_FOUND,
...         )

>>> response = MissingUserController.as_view()(DMRRequestFactory().get('/'))
>>> response.status_code
404
>>> json.loads(response.content)
{'errors': [{'status': '404', 'code': 'user_not_found', 'detail': 'User does not exist', 'source': {'parameter': 'user_id'}}]}

```

`status` is always filled in for you and always matches the HTTP status code.
Like with any `django-modern-rest` response, declare the status codes
that you return, unless you turn off response validation.
Several error objects can be passed to one `JsonApiError`.

## Documents and pagination

`dmr_jsonapi.builders` has small functions for the repetitive parts:
`resource_identifier`, `resource_object`, `relationship_to_one`,
`relationship_to_many`, `document`, and `pagination_links`.
They only include members that you pass, ids are converted to strings.

```python
>>> from django.test import RequestFactory
>>> from dmr_jsonapi.builders import pagination_links

>>> request = RequestFactory().get('/users/', {'page[number]': '2'})
>>> links = pagination_links(request, number=2, size=10, total=25)
>>> links['next']
'http://testserver/users/?page%5Bnumber%5D=3&page%5Bsize%5D=10'
>>> links['last']
'http://testserver/users/?page%5Bnumber%5D=3&page%5Bsize%5D=10'

```

## What `JsonApiController` does

- Uses `JsonApiParser` and `JsonApiRenderer` by default.
  Both use `msgspec` when it is installed, same as `django-modern-rest`.
- Responds with `415` if a request body has `Content-Type` parameters
  other than `ext` and `profile`. Pass `allowed_params=` to `JsonApiParser`
  if you need to relax it, for example to accept `charset`.
- Responds with `406` if every JSON:API media type in `Accept`
  has parameters other than `ext` and `profile`.
- Uses `ErrorDocument` as the error model in the OpenAPI schema.

You can use the parser and the renderer without the controller too,
add them to `parsers` and `renderers` of any `django-modern-rest` controller
or to the `DMR_SETTINGS`.

## Not supported yet

- Parsing of `include`, `fields[...]`, `sort`, and `filter` query parameters,
  you can describe them with regular `Query` components
- Endpoints for relationships (`/users/1/relationships/posts/`)
- Negotiation of `ext` and `profile` media type parameters,
  they are accepted, but ignored
- JSON:API errors for `404` and `500` handlers of the whole project,
  `build_404_handler` and `build_500_handler` return the default format

## Development

We use [uv](https://github.com/astral-sh/uv) and
[just](https://github.com/casey/just), see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
