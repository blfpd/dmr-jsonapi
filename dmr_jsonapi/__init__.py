"""JSON:API support for ``django-modern-rest``."""

from dmr_jsonapi.constants import JSON_API_CONTENT_TYPE as JSON_API_CONTENT_TYPE
from dmr_jsonapi.controller import JsonApiController as JsonApiController
from dmr_jsonapi.errors import JsonApiError as JsonApiError
from dmr_jsonapi.parsers import JsonApiParser as JsonApiParser
from dmr_jsonapi.renderers import JsonApiRenderer as JsonApiRenderer
