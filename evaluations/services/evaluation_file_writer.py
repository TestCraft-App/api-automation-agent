"""Service for writing evaluation output files to disk."""

import os
from typing import List

from src.ai_tools.models.file_spec import FileSpec
from src.utils.logger import Logger


class EvaluationFileWriter:
    """Service for persisting generated evaluation files."""

    def __init__(self):
        """Initialize the Evaluation File Writer."""
        self.logger = Logger.get_logger(__name__)

    def save_generated_files(self, generated_files: List[FileSpec], output_dir: str) -> List[str]:
        """
        Persist generated files to disk within the specified output directory.

        Args:
            generated_files: List of generated FileSpec objects.
            output_dir: Destination directory to save the files.

        Returns:
            List of absolute paths to the saved files.
        """
        saved_paths: List[str] = []

        for file in generated_files:
            relative_path = file.path.lstrip("/\\")
            destination_path = os.path.join(output_dir, relative_path)
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)

            try:
                with open(destination_path, "w", encoding="utf-8") as f:
                    f.write(file.fileContent)
                absolute_path = os.path.abspath(destination_path)
                saved_paths.append(absolute_path)
                self.logger.debug("Saved generated file to %s", absolute_path)
            except Exception as e:
                self.logger.error("Failed to save generated file %s: %s", destination_path, e)

        return saved_paths
