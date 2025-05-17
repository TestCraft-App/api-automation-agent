from dataclasses import dataclass, field
from typing import List, Optional

from src.models.api_def import APIDef
from src.models.api_path import APIPath
from src.models.api_verb import APIVerb
from src.processors.postman.models import RequestData


@dataclass
class APIDefinition:
    """Container for API definitions and their endpoints"""

    definitions: List[APIDef | RequestData] = field(default_factory=list)
    endpoints: Optional[List[str]] = None

    def add_definition(self, definition: APIDef) -> None:
        """Add a definition to the list"""
        self.definitions.append(definition)

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
        return {"definitions": [d.to_json() for d in self.definitions], "endpoints": self.endpoints}
