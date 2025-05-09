from typing import List

from pydantic import BaseModel, Field

from .file_spec import FileSpec


class FileCreationInput(BaseModel):
    files: List[FileSpec] = Field(
        description="A list of dicts, each containing a 'path' and 'fileContent' key. "
        "'fileContent' should be a valid JSON string enclosed in double quotes, with any "
        "special characters properly escaped.",
        examples=[
            [
                {"path": "file1.txt", "fileContent": "'Hello, World!'"},
                {"path": "file2.json", "fileContent": "{ 'key': 'value' }"},
                {"path": "file3.ts", "fileContent": "export const x = 5;"},
            ]
        ],
    )
