import logging
import os
from typing import List, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from src.ai_tools.models.file_reading_input import FileReadingInput
from .models.file_spec import FileSpec
from ..configuration.config import Config
from ..services.file_service import FileService
from ..utils.logger import Logger


class FileReadingTool(BaseTool):
    name: str = "read_files"
    description: str = (
        "Reads the content of all files specified by path and returns the concat of all contents"
    )
    args_schema: Type[BaseModel] = FileReadingInput
    config: Config = None
    file_service: FileService = None
    logger: logging.Logger = None

    def __init__(self, config: Config, file_service: FileService):
        super().__init__()
        self.config = config
        self.file_service = file_service
        self.logger = Logger.get_logger(__name__)

    def _run(self, files: List[str]) -> List[FileSpec]:
        all_read_files = []

        for file_path in files:
            try:
                file_content = self.file_service.read_file(
                    os.path.join(self.config.destination_folder, file_path)
                )
            except Exception as e:
                self.logger.error(f"Error reading file {file_path}: {e}")
                file_content = None

            if file_content:
                file_spec = FileSpec(path=file_path, fileContent=file_content)
                all_read_files.append(file_spec)

        self.logger.info(f"Successfully read {len(all_read_files)} files")
        return all_read_files

    # TODO: Implement async file reading
    async def _arun(self, files: List[str]) -> List[FileSpec]:
        return self._run(files)
