# Version history

We follow [Semantic Versioning](https://semver.org/).
Until `1.0.0` minor releases can contain breaking changes.

## 0.1.2

- Fixes `source` of errors from `msgspec` validation:
  field names with brackets, like `page[size]`, become `source.parameter`
  or `source.pointer` instead of their parent
- Unknown fields, like `?sort=`, get their own `source` instead of none
- Dict keys, shown as `[...]` by `msgspec`, point to the dict
  instead of a wrong index

## 0.1.0

Initial release.

- Adds `JsonApiController`, `JsonApiParser`, and `JsonApiRenderer`
  for `application/vnd.api+json`
- Adds typed models for JSON:API objects in `dmr_jsonapi.objects`
- Adds builders for documents, resources, relationships,
  and pagination links in `dmr_jsonapi.builders`
- Renders all errors as JSON:API error documents,
  adds `JsonApiError` and `error_object`
- Responds with `415` and `406` for unsupported media type parameters
