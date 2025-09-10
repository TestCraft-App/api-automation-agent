from dataclasses import dataclass, field
from typing import Dict, Any, List

from src.models.generated_model import GeneratedModel


@dataclass
class ModelInfo:
    """Represents information about generated models"""

    path: str
    files: Dict[str, str] = field(default_factory=dict)
    models: List[GeneratedModel] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        """Convert the model info to a JSON-serializable dictionary"""
        return {"path": self.path, "files": self.files, "models": [model.to_json() for model in self.models]}

    def add_model(self, model: GeneratedModel) -> None:
        """Add a model to the list of models"""
        self.models.append(model)
        self.files[model.path] = f"{model.path} - {model.summary}"

    def get_models_by_path(self, path: str) -> List[GeneratedModel]:
        """Get all models that match the given path"""
        return [model for model in self.models if model.path == path]

    def get_models_by_summary(self, summary: str) -> List[GeneratedModel]:
        """Get all models that match the given summary"""
        return [model for model in self.models if summary in model.summary]
