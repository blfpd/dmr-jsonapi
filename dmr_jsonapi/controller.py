from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, Final

from django.http import HttpRequest
from django.http.response import HttpResponse, HttpResponseBase
from dmr import Controller
from dmr.cookies import NewCookie
from dmr.errors import ErrorType
from dmr.exceptions import NotAcceptableError
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from typing_extensions import TypeVar, override

from dmr_jsonapi.errors import format_error, with_status
from dmr_jsonapi.negotiation import is_accept_unsatisfiable
from dmr_jsonapi.objects import ErrorDocument
from dmr_jsonapi.parsers import JsonApiParser
from dmr_jsonapi.renderers import JsonApiRenderer

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)

_NOT_ACCEPTABLE_MSG: Final = (
    'All JSON:API media types in `Accept` have parameters'
    ' that are not supported'
)
_NOT_ALLOWED_MSG: Final = 'Method {method} is not allowed, allowed: {allowed}'

# Used for responses that are built before the negotiation happens:
_FALLBACK_RENDERER: Final = JsonApiRenderer()


class JsonApiController(Controller[_SerializerT]):
    """
    Base controller for JSON:API endpoints.

    What it does:

    - Parses and renders ``application/vnd.api+json``
    - Returns all errors, including ones that ``django-modern-rest`` raises
      by itself, as JSON:API error documents
    - Sets ``status`` of errors to the HTTP status code of a response
    - Responds with ``406`` when ``Accept`` can't be satisfied

    Use it like any other reusable controller:

    .. code:: python

        >>> from dmr.plugins.pydantic import PydanticSerializer
        >>> from dmr_jsonapi import JsonApiController

        >>> class UserController(JsonApiController[PydanticSerializer]):
        ...     pass

    """

    parsers = (JsonApiParser(),)
    renderers = (JsonApiRenderer(),)
    error_model = ErrorDocument

    @override
    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseBase:
        """Check ``Accept`` header the way JSON:API wants it."""
        if is_accept_unsatisfiable(request.META.get('HTTP_ACCEPT')):
            response = self.to_error(
                self.format_error(
                    NotAcceptableError(_NOT_ACCEPTABLE_MSG),
                ),
                status_code=HTTPStatus.NOT_ACCEPTABLE,
                # Negotiation did not happen, so we choose the renderer:
                renderer=_FALLBACK_RENDERER,
            )
            return _respond(response, is_async=self.is_async)
        return super().dispatch(request, *args, **kwargs)

    @override
    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
    ) -> ErrorDocument:
        """Convert an error to a JSON:API error document."""
        return format_error(error, loc=loc, error_type=error_type)

    @override
    def handle_method_not_allowed(self, method: str) -> HttpResponse:
        """Return ``405`` as a JSON:API error document."""
        allowed_methods = sorted(self.api_endpoints)
        response = self.to_error(
            self.format_error(
                _NOT_ALLOWED_MSG.format(
                    method=repr(method),
                    allowed=repr(allowed_methods),
                ),
                error_type=ErrorType.not_allowed,
            ),
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
            headers={'Allow': ', '.join(allowed_methods)},
            renderer=_FALLBACK_RENDERER,
        )
        return _respond(response, is_async=self.is_async)

    @override
    def to_error(
        self,
        raw_data: Any,
        *,
        status_code: HTTPStatus,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        renderer: Renderer | None = None,
    ) -> HttpResponse:
        """Make sure that ``status`` of errors matches the response."""
        return super().to_error(
            with_status(raw_data, status_code),
            status_code=status_code,
            headers=headers,
            cookies=cookies,
            renderer=renderer,
        )


async def _awaitable(response: HttpResponse) -> HttpResponse:
    return response


def _respond(response: HttpResponse, *, is_async: bool | None) -> HttpResponse:
    # Async controllers must return awaitable responses from `dispatch`.
    # Type annotations of `dispatch` don't know about it, same as in `dmr`.
    return _awaitable(response) if is_async else response  # type: ignore[return-value]
