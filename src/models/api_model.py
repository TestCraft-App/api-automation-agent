from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class APIModel:
    """Base class for API models"""

    path: str
    files: List[str] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        """Convert the model to a JSON-serializable dictionary"""
        return {"path": self.path, "files": self.files}


def api_models_to_json(list_of_models: List[APIModel]) -> List[Dict[str, Any]]:
    """Convert a list of API models to a JSON-serializable dictionary"""
    return [model.to_json() for model in list_of_models]
