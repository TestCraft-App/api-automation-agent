from dataclasses import dataclass, field
from typing import Dict, Any, List

from src.models.model_info import ModelInfo


@dataclass
class GeneratedModels:
    """Container for all generated models"""

    info: List[ModelInfo] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        """Convert the generated models to a JSON-serializable dictionary"""
        return {"info": [model_info.to_json() for model_info in self.info]}
