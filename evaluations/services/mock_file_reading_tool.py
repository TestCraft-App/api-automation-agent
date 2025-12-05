"""Mock FileReadingTool for evaluation that returns stub content without reading files."""

import logging
from typing import List, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from src.ai_tools.models.file_reading_input import FileReadingInput
from src.ai_tools.models.file_spec import FileSpec
from src.utils.logger import Logger


class MockFileReadingTool(BaseTool):
    """
    Mock version of FileReadingTool for evaluation purposes.

    Returns FileSpec objects with stub content for any requested file path,
    without actually reading files from disk. This allows evaluation of
    get_additional_models without needing real files.
    """

    name: str = "read_files"
    description: str = (
        "Reads the content of all files specified by path and returns the concat of all contents"
    )
    args_schema: Type[BaseModel] = FileReadingInput
    logger: logging.Logger = None

    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger(__name__)

    def _run(self, files: List[str]) -> List[FileSpec]:
        """Return stub FileSpec objects for all requested files."""
        all_read_files = []

        for file_path in files:
            file_spec = FileSpec(path=file_path, fileContent=f"// Stub content for {file_path}")
            all_read_files.append(file_spec)

        self.logger.info(f"Mock read {len(all_read_files)} files")
        return all_read_files

    async def _arun(self, files: List[str]) -> List[FileSpec]:
        return self._run(files)
