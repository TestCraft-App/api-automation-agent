from typing import Dict, Any
from .base_schema_filter import BaseSchemaFilter


class OpenAPIv2SchemaFilter(BaseSchemaFilter):
    def get_schemas_from_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        if "definitions" not in spec:
            return {}

        return spec["definitions"]

    def collect_used_schemas(self, schemas: Dict[str, Any], refs_on_paths: set) -> Dict[str, Any]:
        """Returns only the referenced schemas."""
        used_schemas = {}
        refs_to_check = list(refs_on_paths)

        while refs_to_check:
            ref = refs_to_check.pop()
            if not ref.startswith("#/definitions/"):
                continue

            schema_name = ref.split("/")[-1]
            if schema_name in used_schemas:
                continue

            schema = schemas.get(schema_name)
            if not schema:
                continue

            used_schemas[schema_name] = schema

            nested_refs = super().collect_refs(schema)
            refs_to_check.extend(nested_refs)

        return used_schemas

    def add_filtered_schemas(self, spec, filtered_schemas):
        spec["definitions"] = filtered_schemas
        return spec
