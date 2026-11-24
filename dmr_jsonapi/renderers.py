from dmr.internal.json import JsonModule
from dmr.parsers import JsonParser
from dmr.renderers import JsonRenderer
from typing_extensions import override

from dmr_jsonapi._json import default_json_module
from dmr_jsonapi.constants import JSON_API_CONTENT_TYPE


class JsonApiRenderer(JsonRenderer):
    """
    Renders responses as ``application/vnd.api+json``.

    Uses ``msgspec`` when it is installed, the same way ``django-modern-rest``
    does it by default. Alternative json backends can be passed
    with *json_module*, see ``django-modern-rest`` docs.

    It only sets the right media type. Documents themselves are built
    by your code, see :mod:`dmr_jsonapi.objects`
    and :mod:`dmr_jsonapi.builders`.
    """

    __slots__ = ()

    def __init__(
        self,
        content_type: str = JSON_API_CONTENT_TYPE,
        *,
        json_module: JsonModule = default_json_module,
    ) -> None:
        """Init the renderer with the JSON:API media type by default."""
        super().__init__(content_type, json_module=json_module)

    @property
    @override
    def validation_parser(self) -> JsonParser:
        """
        Plain json parser can parse the result.

        We don't want any media type checks here,
        because there is no incoming request.
        """
        return JsonParser(self.content_type, json_module=self._json_module)
