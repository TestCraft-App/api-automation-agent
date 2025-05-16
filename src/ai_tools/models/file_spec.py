import json
from typing import List, Dict, Any

from pydantic import BaseModel, Field


class FileSpec(BaseModel):
    path: str = Field(description="The relative file path including the filename.")
    fileContent: str = Field(
        description=(
            "The content of the file. This must be a valid JSON string "
            "enclosed in double quotes. Any special characters that could "
            "cause issues when parsing the string as JSON should be escaped using a backslash (\\). "
            "Note: Do not escape single quotes ('), only special characters such as newlines, tabs, etc."
        ),
    )

    def to_json(self):
        return {"path": self.path, "fileContent": self.fileContent}


def file_specs_to_json(file_specs: List[FileSpec]) -> List[Dict[str, Any]]:
    """Convert a list of FileSpec objects to a JSON-serializable dictionary."""
    return [file_spec.to_json() for file_spec in file_specs]


def convert_to_file_spec(data: Any) -> List[FileSpec]:
    """
    Convert a dictionary to a FileSpec object.

    Args:
        data (Any): Data to convert

    Returns:
        List[FileSpec]: List of FileSpec objects
    """
    if isinstance(data, List):
        if len(data) > 0 and isinstance(data[0], FileSpec):
            return data

    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, List):
        print(data)
        return [FileSpec(**file_spec) for file_spec in data]
    return []
