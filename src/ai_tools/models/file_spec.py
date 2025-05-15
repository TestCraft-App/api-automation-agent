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
