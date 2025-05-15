from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class GeneratedModel:
    """Represents a generated model with its metadata"""

    path: str
    fileContent: str
    summary: str

    def to_json(self) -> Dict[str, Any]:
        """Convert the model to a JSON-serializable dictionary"""
        return {"path": self.path, "fileContent": self.fileContent, "summary": self.summary}

    @staticmethod
    def is_response_file(path: str) -> bool:
        """Check if the file is a response interface"""
        return "/responses" in path


def generated_models_to_json(list_of_models: List[GeneratedModel]) -> List[Dict[str, Any]]:
    """Convert a list of models to a JSON-serializable dictionary"""
    return [model.to_json() for model in list_of_models]
