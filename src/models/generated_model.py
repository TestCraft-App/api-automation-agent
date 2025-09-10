from dataclasses import dataclass
from typing import Dict, Any, List

from src.ai_tools.models.model_file_spec import ModelFileSpec


@dataclass
class GeneratedModel:
    """Represents a generated model with its metadata"""

    path: str
    fileContent: str = ""
    summary: str = ""

    def to_json(self) -> Dict[str, Any]:
        """Convert the model to a JSON-serializable dictionary"""
        json = {"path": self.path}
        if self.fileContent:
            json["fileContent"] = self.fileContent
        if self.summary:
            json["summary"] = self.summary
        return json

    @staticmethod
    def is_response_file(path: str) -> bool:
        """Check if the file is a response interface"""
        return "/responses" in path

    @staticmethod
    def from_model_file_specs(file_specs: List[ModelFileSpec]) -> List["GeneratedModel"]:
        """Create a GeneratedModel from a file spec dictionary"""
        return [
            GeneratedModel(
                path=file_spec.path,
                fileContent=file_spec.fileContent,
                summary=file_spec.summary,
            )
            for file_spec in file_specs
        ]

    @staticmethod
    def list_to_json(list_of_models: List["GeneratedModel"]) -> List[Dict[str, Any]]:
        """Convert a list of models to a JSON-serializable dictionary"""
        return [model.to_json() for model in list_of_models]
