from typing import List, Dict, Any

from pydantic import BaseModel, Field

from .file_spec import FileSpec


class FileCreationInput(BaseModel):
    files: List[Dict[str, Any]] = Field(
        description="A list of dicts, each containing a 'path' (string) and 'fileContent' (string) key. "
        "'fileContent' should be a valid TypeScript/JavaScript code string with proper escaping for special characters.",
        examples=[
            [
                {"path": "file1.txt", "fileContent": "'Hello, World!'"},
                {"path": "file2.json", "fileContent": "{ 'key': 'value' }"},
                {"path": "file3.ts", "fileContent": "export const x = 5;"},
            ]
        ],
    )
