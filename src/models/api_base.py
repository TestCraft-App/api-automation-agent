from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class APIBase:
    """Base class for API components"""

    path: str
    yaml: str
    type: str

    def to_json(self) -> Dict[str, Any]:
        """Convert the component to a JSON-serializable dictionary"""
        return {"path": self.path, "yaml": self.yaml, "type": self.type}

    @staticmethod
    def get_root_path(path: str) -> str:
        """Gets the root path from a full path, preserving version numbers if present."""
        path_no_query = path.split("?")[0]
        parts = path_no_query.strip("/").split("/")
        if len(parts) > 1 and parts[0].startswith("v") and parts[0][1].isdigit():
            return "/" + "/".join(parts[:2])
        return "/" + parts[0]
