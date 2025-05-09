from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class APIModel:
    """Base class for API models"""

    path: str
    files: List[str] = field(default_factory=list)
    models: List[Dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        """Convert the model to a JSON-serializable dictionary"""
        return {"path": self.path, "files": self.files, "models": self.models}
