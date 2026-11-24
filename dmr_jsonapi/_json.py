from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from dmr.internal.json import JsonModule, NativeJson

if TYPE_CHECKING:
    from dmr.parsers import Raw

try:
    import msgspec
except ImportError:  # pragma: no cover
    default_json_module: JsonModule = NativeJson
else:

    class _MsgspecJson:  # noqa: WPS431
        """Json module for ``dmr`` that is based on ``msgspec``."""

        __slots__ = ()

        @classmethod
        def dumps(
            cls,
            to_serialize: Any,
            /,
            default: Callable[[Any], Any] | None = None,
        ) -> bytes:
            """Dump an object to json bytes."""
            return msgspec.json.encode(to_serialize, enc_hook=default)

        @classmethod
        def loads(cls, to_deserialize: 'str | Raw', /) -> Any:
            """Load a simple object from json."""
            return msgspec.json.decode(to_deserialize)

    default_json_module = _MsgspecJson
