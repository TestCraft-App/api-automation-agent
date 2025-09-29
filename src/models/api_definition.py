from dataclasses import dataclass, field
from typing import List, Optional, Dict
from typing import Any
from src.models.api_def import APIDef
from src.models.api_path import APIPath
from src.models.api_verb import APIVerb
from src.processors.postman.models import RequestData
import yaml


@dataclass
class APIDefinition:
    """Container for API definitions and their endpoints"""

    definitions: List[APIDef | RequestData] = field(default_factory=list)
    endpoints: Optional[List[str]] = None
    variables: List[Dict[str, str]] = field(default_factory=list)
    base_yaml: Optional[str] = None
    info: Dict[str, Any] = field(default_factory=dict)   # 👈 add info field
    paths: List[APIPath] = field(default_factory=list) 

    def add_definition(self, definition: APIDef) -> None:
        """Add a definition to the list"""
        self.definitions.append(definition)

    def add_variable(self, key: str, value: str) -> None:
        """Add a variable to the list"""
        self.variables.append({"key": key, "value": value})

    def get_paths(self) -> List[APIPath]:
        """Get all path definitions"""
        return [d for d in self.definitions if isinstance(d, APIPath)]

    def get_verbs(self) -> List[APIVerb]:
        """Get all verb definitions"""
        return [d for d in self.definitions if isinstance(d, APIVerb)]

    def should_process_endpoint(self, path: str) -> bool:
        """Check if an endpoint should be processed based on configuration"""
        if self.endpoints is None:
            return True
        return any(path.startswith(endpoint) for endpoint in self.endpoints)

    def get_filtered_paths(self) -> List[APIPath]:
        """Get all path definitions that should be processed"""
        return [
            path
            for path in self.get_paths()
            if isinstance(path, APIPath) and self.should_process_endpoint(path.path)
        ]

    def get_filtered_verbs(self) -> List[APIVerb]:
        """Get all verb definitions that should be processed"""
        return [
            verb
            for verb in self.get_verbs()
            if isinstance(verb, APIVerb) and self.should_process_endpoint(verb.path)
        ]

    def to_json(self) -> dict:
        """Convert to JSON-serializable dictionary"""
        return {
            "definitions": [d.to_json() for d in self.definitions],
            "endpoints": self.endpoints,
            "variables": self.variables,
            "base_yaml": self.base_yaml,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "APIDefinition":
        """
        Convert a dictionary (parsed from YAML/JSON) into an APIDefinition instance.
        Supports both Swagger 2.x (definitions) and OpenAPI 3.x (components).
        """
        definitions = []

        # --- Process schema definitions ---
        if "definitions" in data:  # Swagger 2.x
            for name, schema in data["definitions"].items():
                try:
                    definitions.append(APIDef.from_dict({name: schema}))
                except Exception:
                    definitions.append({name: schema})

        if "components" in data and "schemas" in data["components"]:  # OpenAPI 3.x
            for name, schema in data["components"]["schemas"].items():
                try:
                    definitions.append(APIDef.from_dict({name: schema}))
                except Exception:
                    definitions.append({name: schema})

        # --- Process paths/endpoints ---
        if "paths" in data:
            for path, verbs in data["paths"].items():
                # Store the path (dump dict → YAML string for safe storage)
                api_path = APIPath(
                    path=path,
                    yaml=yaml.dump(verbs) if isinstance(verbs, dict) else str(verbs),
                )
                definitions.append(api_path)

                # Store verbs under this path
                for verb, verb_content in verbs.items():
                    if verb.lower() in ["get", "post", "put", "delete", "patch", "options", "head"]:
                        api_verb = APIVerb(
                            verb=verb.upper(),
                            path=path,
                            root_path=APIPath.normalize_path(path),
                            yaml=yaml.dump(verb_content) if isinstance(verb_content, dict) else str(verb_content),
                        )
                        definitions.append(api_verb)

        # --- Extract info (title, version, etc.) ---
        info = data.get("info", {})

        return cls(
            definitions=definitions,
            endpoints=data.get("endpoints"),
            variables=data.get("variables", []),
            base_yaml=data.get("base_yaml"),
            info=info,
        )