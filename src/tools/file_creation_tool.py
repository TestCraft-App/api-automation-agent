import json
import os
from typing import List, Type, Dict, Any

from langchain_core.tools import BaseTool
from pydantic import Field, BaseModel

from src.config import args


class FileSpec(BaseModel):
    path: str = Field(description="The relative file path including the filename")
    fileContent: str = Field(description="The content to be written to the file")


class FileCreationInput(BaseModel):
    files: List[FileSpec] = Field(
        description="A list of dicts, each containing a path and fileContent key",
        examples=[[{"path": "file.txt", "fileContent": "Hello, World!"}]],
    )


class FileCreationTool(BaseTool):
    name: str = "create_files"
    description: str = "Create files with a given content."
    args_schema: Type[BaseModel] = FileCreationInput

    def _run(self, files: List[FileSpec]) -> str:
        for file_spec in files:
            path = file_spec.path
            content = file_spec.fileContent
            if path.startswith("./"):
                path = path[2:]
            updated_path = os.path.join(args.destination_folder, path)
            os.makedirs(os.path.dirname(updated_path), exist_ok=True)
            with open(updated_path, "w") as f:
                f.write(content)
            print(f"Created file: {path}")

        return json.dumps([file_spec.model_dump() for file_spec in files])

    async def _arun(self, files: List[FileSpec]) -> str:
        return self._run(files)

    def _parse_input(self, tool_input: str | Dict) -> Dict[str, Any]:
        if isinstance(tool_input, str):
            data = json.loads(tool_input)
        else:
            data = tool_input

        if isinstance(data["files"], str):
            files_data = json.loads(data["files"])
        else:
            files_data = data["files"]

        file_specs = [FileSpec(**file_spec) for file_spec in files_data]
        return {"files": file_specs}
