import json
from typing import Any, List

from pydantic import Field

from .file_spec import FileSpec


class ModelFileSpec(FileSpec):
    summary: str = Field(
        description=(
            "A concise summary of the file's content using this format: "
            "For services: '<Name> service: <comma-separated list of methods>' "
            "For models: '<Name> model. Properties: <comma-separated list of properties>' "
            "For other files: A single sentence describing the file's main purpose."
        )
    )

    def to_json(self):
        return {
            "path": self.path,
            "fileContent": self.fileContent,
            "summary": self.summary,
        }


def convert_to_model_file_spec(data: Any) -> List[ModelFileSpec]:
    """
    Convert a dictionary to a ModelFileSpec object.

    Args:
        data (Any): Data to convert

    Returns:
        List[ModelFileSpec]: List of ModelFileSpec objects
    """
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, List):
        if len(data) > 0 and isinstance(data[0], ModelFileSpec):
            return data
        return [ModelFileSpec(**file_spec) for file_spec in data]
    return []
