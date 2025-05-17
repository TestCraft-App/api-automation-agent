import re
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class APIVerb:
    """Represents an API verb (HTTP method) with its metadata"""

    verb: str
    path: str
    root_path: str
    yaml: str
    type: str = "verb"

    def to_json(self) -> Dict[str, Any]:
        """Convert the verb to a JSON-serializable dictionary"""
        return {
            "verb": self.verb,
            "path": self.path,
            "root_path": self.root_path,
            "yaml": self.yaml,
            "type": self.type,
        }

    @staticmethod
    def get_root_path(path: str) -> str:
        """Gets the root path from a full path."""
        match = re.match(r"(/[^/?]+)", path)
        if match:
            return match.group(1)
        return path
