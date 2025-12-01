from dataclasses import dataclass, field
from typing import List
from .api_base import APIBase


@dataclass
class APIVerb(APIBase):
    """Represents an API verb (HTTP method) with its metadata"""

    type: str = field(default="verb", init=False)

    file_path: str = ""
    verb: str = ""
    prerequest: List[str] = field(default_factory=list)
    name: str = ""

    def to_json(self) -> dict:
        """Convert the APIVerb instance to a JSON-serializable dictionary"""
        return {
            "verb": self.verb,
            "path": self.full_path,
            "root_path": self.root_path,
            "yaml": self.content,
            "type": self.type,
        }
