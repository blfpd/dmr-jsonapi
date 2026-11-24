from collections.abc import Mapping, Set
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

from django.http import HttpRequest
from dmr.internal.json import JsonModule
from dmr.metadata import EndpointMetadata, ResponseSpec
from dmr.parsers import DeserializeFunc, JsonParser, Raw
from typing_extensions import TypeForm, override

from dmr_jsonapi._json import default_json_module
from dmr_jsonapi.constants import (
    JSON_API_CONTENT_TYPE,
    JSON_API_MEDIA_PARAMS,
)
from dmr_jsonapi.errors import JsonApiError, error_object

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer

_UNSUPPORTED_PARAMS_MSG: Final = (
    'Media type parameters {params} are not supported for {content_type},'
    ' only {allowed} can be used'
)


class JsonApiParser(JsonParser):
    """
    Parses ``application/vnd.api+json`` request bodies.

    The specification requires servers to respond with ``415``
    when a request has a ``Content-Type`` with media type parameters
    other than ``ext`` and ``profile``. We do that.
    You can change allowed parameters with *allowed_params*.
    """

    __slots__ = ('_allowed_params',)

    def __init__(
        self,
        content_type: str = JSON_API_CONTENT_TYPE,
        *,
        json_module: JsonModule = default_json_module,
        allowed_params: Set[str] = JSON_API_MEDIA_PARAMS,
    ) -> None:
        """Init the parser with the JSON:API media type by default."""
        super().__init__(content_type, json_module=json_module)
        self._allowed_params = allowed_params

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: TypeForm[Any],
    ) -> Any:
        """
        Decode a JSON:API body.

        Raises:
            JsonApiError: With ``415`` status code
                when media type has unsupported parameters.
            DataParsingError: If error decoding *to_deserialize*.

        """
        # `django` strips parameters from `content_type`, but keeps them here:
        unsupported = sorted(
            set(getattr(request, 'content_params', None) or ())
            - self._allowed_params,
        )
        if unsupported:
            raise JsonApiError(
                error_object(
                    _UNSUPPORTED_PARAMS_MSG.format(
                        params=unsupported,
                        content_type=self.content_type,
                        allowed=sorted(self._allowed_params),
                    ),
                    code='unsupported_media_type',
                    source={'header': 'Content-Type'},
                ),
                status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            )
        return super().parse(
            to_deserialize,
            deserializer_hook,
            request=request,
            model=model,
        )

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Describe the ``415`` error that this parser can produce."""
        return self._add_new_response(
            ResponseSpec(
                return_type=controller_cls.error_model,
                status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                description=(
                    'Raised when `Content-Type` has unsupported'
                    ' media type parameters'
                ),
            ),
            existing_responses,
        )
