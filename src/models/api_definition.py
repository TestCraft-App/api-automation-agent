from dataclasses import dataclass, field
from typing import List, Optional, Dict

from src.models.api_def import APIDef
from src.models.api_path import APIPath
from src.models.api_verb import APIVerb
from src.processors.postman.models import RequestData


@dataclass
class APIDefinition:
    """Container for API definitions and their endpoints"""

    definitions: List[APIDef | RequestData] = field(default_factory=list)
    endpoints: Optional[List[str]] = None
    variables: List[Dict[str, str]] = field(default_factory=list)
    base_yaml: Optional[str] = None

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
        path_no_slash = path.lstrip("/")
        return any(path_no_slash.startswith(endpoint.lstrip("/")) for endpoint in self.endpoints)

    def to_json(self) -> dict:
        """Convert to JSON-serializable dictionary"""
        return {
            "definitions": [d.to_json() for d in self.definitions],
            "endpoints": self.endpoints,
            "variables": self.variables,
            "base_yaml": self.base_yaml,
        }
