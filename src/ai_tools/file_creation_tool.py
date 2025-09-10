import json
import logging
from typing import List, Optional, Type, Dict, Any

import json_repair
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from .models.file_creation_input import FileCreationInput
from .models.file_spec import FileSpec
from .models.model_creation_input import ModelCreationInput
from .models.model_file_spec import ModelFileSpec
from ..configuration.config import Config
from ..services.file_service import FileService
from ..utils.logger import Logger


class FileCreationTool(BaseTool):
    name: str = "create_files"
    description: str = "Create files with a given content."
    args_schema: Type[BaseModel] = FileCreationInput
    config: Config = None
    file_service: FileService = None
    logger: logging.Logger = None
    are_models: bool = False

    def __init__(self, config: Config, file_service: FileService, are_models: bool = False):
        super().__init__()
        self.config = config
        self.file_service = file_service
        self.logger = Logger.get_logger(__name__)
        self.are_models = are_models

        if are_models:
            self.args_schema = ModelCreationInput
            self.name = "create_models"
            self.description = "Create models from a given API definition."

    def _is_protected(self, path: str) -> bool:
        for protected in self.config.protected_files or []:
            if path == protected or path.startswith(protected):
                return True
        return False

    def _run(self, files: List[FileSpec | ModelFileSpec]) -> str:
        filtered_files = [f for f in files if not self._is_protected(f.path)]
        skipped = [f.path for f in files if self._is_protected(f.path)]
        if skipped:
            self.logger.info(f"Skipped protected files: {skipped}")
        if not filtered_files:
            return json.dumps([])
        try:
            created_files = self.file_service.create_files(
                destination_folder=self.config.destination_folder, files=filtered_files
            )
            self.logger.info(f"Successfully created {len(created_files)} files")
            return json.dumps([file_spec.model_dump() for file_spec in filtered_files])
        except Exception as e:
            self.logger.error(f"Error creating files: {e}")
            raise

    async def _arun(self, files: List[FileSpec | ModelFileSpec]) -> str:
        return self._run(files)

    def _parse_input(self, tool_input: str | Dict, tool_call_id: Optional[str] = None) -> Dict[str, Any]:
        if isinstance(tool_input, str):
            data = json_repair.loads(tool_input)
        else:
            data = tool_input

        self.logger.debug(f"Received data['files']: {data.get('files', 'Not found')}")

        if not isinstance(data, dict):
            return {"files": []}

        if isinstance(data["files"], str):
            files_data = json_repair.loads(data["files"])
        else:
            files_data = data["files"]

        if not isinstance(files_data, list):
            return {"files": []}

        # Filter out non-dictionary objects
        valid_files = [f for f in files_data if isinstance(f, dict)]
        if len(valid_files) != len(files_data):
            self.logger.info(f"Filtered out {len(files_data) - len(valid_files)} invalid file specifications")

        spec_class = ModelFileSpec if self.are_models else FileSpec
        file_specs = [spec_class(**file_spec) for file_spec in valid_files]
        for file_spec in file_specs:
            if file_spec.path.startswith("/"):
                file_spec.path = f".{file_spec.path}"
        return {"files": file_specs}
