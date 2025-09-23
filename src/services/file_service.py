import ast
import os
import shutil
import sys
from typing import List, Optional

from ..ai_tools.models.file_spec import FileSpec
from ..utils.logger import Logger


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class FileService:
    """
    Service for handling file operations.
    """

    def __init__(self):
        """
        Initialize FileService.
        """
        self.logger = Logger.get_logger(__name__)

    def copy_framework_template(self, destination_folder: str) -> Optional[str]:
        """
        Copy the API framework template to a new folder.

        Args:
            destination_folder (str): Destination folder to copy the template to

        Returns:
            Optional[str]: The destination folder if successful, None otherwise
        """
        src_folder = get_resource_path("api-framework-template")
        self.logger.info("Generating new framework...")
        try:
            # For dirs_exist_ok=True, dst must be a directory.
            # The benchmark runner ensures destination_folder is an existing, empty dir.
            shutil.copytree(src_folder, destination_folder, dirs_exist_ok=True)
            self.logger.info("Framework template generated successfully.")
            return destination_folder
        except Exception as e:
            self.logger.error(f"Error copying folder: {e}")
            return None

    def create_files(self, destination_folder: str, files: List[FileSpec]) -> List[str]:
        """
        Create files with the specified content.

        Args:
            destination_folder (str): Base folder to create the files in
            files (List[FileSpec]): List of FileSpec objects defining paths and content

        Returns:
            List[str]: List of paths to the created files
        """
        created_files = []
        for file_spec in files:
            try:
                path = file_spec.path
                content = file_spec.fileContent

                # For cases like '"import ....\n"' or "'import ....\n'"
                if len(content) >= 2 and content[0] == content[-1] and content[0] in ('"', "'"):
                    try:
                        # ast.literal_eval will strip the quotes AND un-escape \n, \", etc.
                        file_spec.fileContent = ast.literal_eval(content)
                    except (ValueError, SyntaxError):
                        # if it fails, leave it as-is
                        pass

                if path.startswith("./"):
                    path = path[2:]
                path = path.lstrip("/")
                updated_path = os.path.join(destination_folder, path)
                os.makedirs(os.path.dirname(updated_path), exist_ok=True)
                with open(updated_path, "w") as f:
                    f.write(content)

                self.logger.info(f"Created file: {path}")
                created_files.append(updated_path)
            except Exception as e:
                self.logger.error(f"Failed to create file {file_spec.path}: {e}")
        return created_files

    def read_file(self, file_path: str) -> Optional[str]:
        """
        Read file content specified by path.

        Args:
            file_path (str): File path to read.

        Returns:
            Optional[str]: File contents if successful, None if file cannot be read.
        """
        try:
            with open(file_path, "r") as file:
                return file.read()
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            return None
