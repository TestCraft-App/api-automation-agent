import copy
from abc import ABC, abstractmethod
from typing import Dict, Any, Set


class BaseSchemaFilter(ABC):
    """Template base class for filtering schemas in API definitions."""

    def filter(self, api_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Main template method for filtering schemas in an API definition."""
        spec = copy.deepcopy(api_definition)

        if "paths" not in spec:
            return spec
        paths = spec["paths"]

        refs_on_paths = self.collect_refs(paths)

        schemas = self.get_schemas_from_spec(spec)
        if not schemas:
            return spec

        filtered_schemas = self.collect_used_schemas(schemas, refs_on_paths)

        self.add_filtered_schemas(spec, filtered_schemas)

        return spec

    @abstractmethod
    def get_schemas_from_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts schemas from the API definition."""
        pass

    @abstractmethod
    def add_filtered_schemas(self, spec: Dict[str, Any], filtered_schemas: Dict[str, Any]) -> None:
        """Adds the filtered schemas back to the API definition."""
        pass

    @abstractmethod
    def collect_used_schemas(self, schemas: Dict[str, Any], refs_on_paths: Set[str]) -> Dict[str, Any]:
        """Returns only the referenced schemas."""
        pass

    def collect_refs(self, api_def: Any, refs: set = None) -> set:
        """Recursively collects all $ref from the API definition."""
        if refs is None:
            refs = set()

        if isinstance(api_def, dict):
            for key, value in api_def.items():
                if key == "$ref" and isinstance(value, str):
                    refs.add(value)
                else:
                    self.collect_refs(value, refs)
        elif isinstance(api_def, list):
            for item in api_def:
                self.collect_refs(item, refs)

        return refs
