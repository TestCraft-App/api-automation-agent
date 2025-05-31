from typing import Dict, List, Any

from ...utils.logger import Logger


class APIComponentsFilter:
    """Reduces API definition components to only those that are necessary."""

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def filter_schemas(self, api_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Filters out unreferenced schemas from the API definition components."""
        filtered_spec = {}
        used_refs = self.collect_refs(api_definition.get("paths", {}))
        components = api_definition.get("components", {})
        filtered_schemas = self.collect_used_schemas(components.get("schemas", {}), used_refs)

        filtered_spec = {
            "openapi": api_definition["openapi"],
            "info": api_definition["info"],
            "paths": api_definition["paths"],
            "components": {},
        }

        # TODO: Create a method to handle this separately.
        for component_name, component_data in components.items():
            if component_name != "schemas":
                filtered_spec["components"][component_name] = component_data

        filtered_spec["components"]["schemas"] = filtered_schemas

        return filtered_spec

    def collect_refs(self, node: Any, refs: List[str] = None) -> List[str]:
        """Recursively collects all $ref in the API paths."""
        if refs is None:
            refs = []

        if isinstance(node, dict):
            for key, value in node.items():
                if key == "$ref":
                    refs.append(value)
                else:
                    self.collect_refs(value, refs)
        return refs

    def collect_used_schemas(self, schemas: Dict[str, Any], used_refs: List[str]) -> Dict[str, Any]:
        """Returns only the referenced schemas."""
        collected_schemas = {}

        for schema_name, schema in schemas.items():
            ref_string = f"#/components/schemas/{schema_name}"
            if ref_string in used_refs:
                collected_schemas[schema_name] = schema
        return collected_schemas
