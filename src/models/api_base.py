from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class APIBase:
    """Base class for API components"""

    content: str = ""
    root_path: Optional[str] = None
    full_path: str = ""
    type: str = ""
    body: Dict[str, Any] = field(default_factory=dict)
    # Raw request body text (useful for Postman bodies that aren't valid JSON due to templates)
    raw_body: str = ""
    script: List[str] = field(default_factory=list)
    # Whether the request requires auth (Postman-only today; safe default for Swagger).
    auth: bool = False

    def __post_init__(self):
        """Derive root_path from full_path if not provided."""
        if self.root_path is None and self.full_path:
            self.root_path = self.get_root_path(self.full_path)

    @staticmethod
    def get_root_path(path: str) -> str:
        """Gets the root path from a full path, preserving version numbers if present."""
        path_no_query = path.split("?")[0]
        parts = path_no_query.strip("/").split("/")
        if len(parts) > 1 and parts[0].startswith("v") and parts[0][1].isdigit():
            return "/" + "/".join(parts[:2])
        return "/" + parts[0]
