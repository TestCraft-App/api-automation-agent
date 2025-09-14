import logging
from typing import List, Optional, Type, Dict

import json_repair
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from .models.test_fix_input import TestFixInput
from .models.model_fix_input import ModelFixInput
from .models.operation_types import FileOperation

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
    file_operation: FileOperation = None

    def __init__(self, config: Config, file_service: FileService, operation: FileOperation):
        super().__init__()
        self.config = config
        self.file_service = file_service
        self.logger = Logger.get_logger(__name__)
        self.file_operation = operation
        self.args_schema = operation.value.input
        self.name = operation.value.tool_name
        self.description = operation.value.description

    def _run(
        self, files: List[FileSpec | ModelFileSpec], changes: Optional[str] = None
    ) -> ModelCreationInput | FileCreationInput | ModelFixInput | TestFixInput:
        try:
            created_files = self.file_service.create_files(
                destination_folder=self.config.destination_folder, files=files
            )
            if self.file_operation in [FileOperation.CREATE_TEST, FileOperation.CREATE_MODELS]:
                self.logger.info(f"Successfully created {len(created_files)} files")
                return self.args_schema(files=files)
            else:
                self.logger.info(f"Successfully fixed {len(created_files)} files")
                return self.args_schema(files=files, changes=changes)

        except Exception as e:
            self.logger.error(f"Error writing to files: {e}")
            raise

    async def _arun(self, files: List[FileSpec | ModelFileSpec]) -> str:
        return self._run(files)

    def _parse_input(
        self, tool_input: str | Dict, tool_call_id: Optional[str] = None
    ) -> FileCreationInput | ModelCreationInput | ModelFixInput | TestFixInput:
        if isinstance(tool_input, str):
            data = json_repair.loads(tool_input)
        else:
            data = tool_input

        if not isinstance(data, dict):
            return {"files": []}

        if isinstance(data["files"], str):
            files_data = json_repair.loads(data["files"])
        else:
            files_data = data["files"]

        if not isinstance(files_data, list):
            return {"files": []}

        valid_files = [f for f in files_data if isinstance(f, dict)]

        if len(valid_files) != len(files_data):
            self.logger.info(f"Filtered out {len(files_data) - len(valid_files)} invalid file specifications")

        file_specs = [self.file_operation.value.output_spec(**file_spec) for file_spec in valid_files]

        for file_spec in file_specs:
            if file_spec.path.startswith("/"):
                file_spec.path = f".{file_spec.path}"

        result = {"files": file_specs}

        if self.file_operation in [
            FileOperation.FIX_MODELS_COMPILATION,
            FileOperation.FIX_TEST_COMPILATION,
            FileOperation.FIX_TEST_EXECUTION,
        ]:
            changes_value = data.get("changes")
            if isinstance(changes_value, str):
                result["changes"] = changes_value
            else:
                result["changes"] = ""

        return result
