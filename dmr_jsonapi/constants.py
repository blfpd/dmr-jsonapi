from typing import Final

#: Media type of all JSON:API documents.
JSON_API_CONTENT_TYPE: Final = 'application/vnd.api+json'

#: The version of the JSON:API specification that we follow.
JSON_API_VERSION: Final = '1.1'

#: Media type parameters that are allowed by the specification.
JSON_API_MEDIA_PARAMS: Final = frozenset(('ext', 'profile'))
