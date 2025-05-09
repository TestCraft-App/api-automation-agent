from dataclasses import dataclass, field
from typing import List, Optional, Union

from src.models.api_path import APIPath
from src.models.api_verb import APIVerb


@dataclass
class APIDefinition:
    """Container for API definitions and their endpoints"""

    definitions: List[Union[APIPath, APIVerb]] = field(default_factory=list)
    endpoints: Optional[List[str]] = None

    def add_definition(self, definition: Union[APIPath, APIVerb]) -> None:
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

    def to_json(self) -> dict:
        """Convert to JSON-serializable dictionary"""
        return {"definitions": [d.to_json() for d in self.definitions], "endpoints": self.endpoints}
