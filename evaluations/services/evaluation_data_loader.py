"""Service for loading evaluation test data from disk."""

import os
import re
from typing import Any, Dict, List, Optional, Sequence

from src.ai_tools.models.file_spec import FileSpec
from src.models.api_model import APIModel
from src.models.generated_model import GeneratedModel
from src.utils.logger import Logger


class EvaluationDataLoader:
    """Service for loading evaluation test data files."""

    def __init__(self, test_data_folder: str):
        """
        Initialize the Evaluation Data Loader.

        Args:
            test_data_folder: Path to folder containing test data (API definition files)
        """
        self.test_data_folder = test_data_folder
        self.logger = Logger.get_logger(__name__)

    def normalize_dataset_path(self, path: str) -> str:
        """
        Normalize a model file path by removing the test prefix from the filename.

        Args:
            path: File path where filename may start with "test_###_"

        Returns:
            Path with test_id prefix removed from filename (e.g., "requests/UserModel.ts")
        """
        directory = os.path.dirname(path)
        filename = os.path.basename(path)

        filename = re.sub(r"^test_\d+_", "", filename)

        if directory:
            return os.path.join(directory, filename)
        return filename

    def load_api_definition(self, api_definition_file: str) -> Optional[str]:
        """
        Load API definition content from the definitions folder within the test data folder.

        Args:
            api_definition_file: Name of the API definition file

        Returns:
            Content of the API definition file, or None if not found
        """
        definitions_folder = os.path.join(self.test_data_folder, "definitions")
        file_path = os.path.join(definitions_folder, api_definition_file)
        if not os.path.exists(file_path):
            self.logger.error(f"API definition file not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading API definition file {file_path}: {e}")
            return None

    def load_models(self, model_files: Sequence[str]) -> List[GeneratedModel]:
        """
        Load model files from the models folder within the test data folder
        and convert them to GeneratedModel objects.
        The test prefix is removed from filenames and 'src/models/' is prepended.

        Args:
            model_files: Iterable of model file paths relative to the models folder
                (e.g., "requests/test_001_UserModel.ts")

        Returns:
            List of GeneratedModel objects with paths like "src/models/requests/UserModel.ts"
        """
        models_folder = os.path.join(self.test_data_folder, "models")
        if not os.path.exists(models_folder):
            models_folder = os.path.join(self.test_data_folder, "src", "models")
        generated_models = []
        for model_file in model_files:
            file_path = os.path.join(models_folder, model_file)
            if not os.path.exists(file_path):
                self.logger.warning(f"Model file not found: {file_path}, skipping")
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                clean_path = self.normalize_dataset_path(model_file)
                final_path = f"src/models/{clean_path}"

                generated_model = GeneratedModel(
                    path=final_path,
                    fileContent=file_content,
                    summary="",  # Models loaded from files don't have summaries
                )
                generated_models.append(generated_model)
                self.logger.debug(f"Loaded model file: {model_file} -> {final_path}")
            except Exception as e:
                self.logger.error(f"Error reading model file {file_path}: {e}")
                continue

        if not generated_models:
            self.logger.warning("No model files were successfully loaded")
        else:
            self.logger.info(f"Successfully loaded {len(generated_models)} model file(s)")

        return generated_models

    def load_first_test_file(self, test_file: Optional[str]) -> Optional[FileSpec]:
        """
        Load the first test file from the tests folder within the test data folder
        and convert it to a FileSpec object.

        Args:
            test_file: Test file path relative to the tests folder.

        Returns:
            FileSpec object with normalized path, or None if not found.
        """
        if not test_file:
            self.logger.warning("No first_test_file provided for generate_additional_tests case")
            return None

        tests_folder = os.path.join(self.test_data_folder, "tests")
        file_path = os.path.join(tests_folder, test_file)
        if not os.path.exists(file_path):
            self.logger.error(f"First test file not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()

            clean_path = self.normalize_dataset_path(test_file)
            final_path = f"src/tests/{clean_path}"
            self.logger.debug(f"Loaded first test file: {test_file} -> {final_path}")
            return FileSpec(path=final_path, fileContent=file_content)
        except Exception as e:
            self.logger.error(f"Error reading first test file {file_path}: {e}")
            return None

    def load_available_models(self, available_models_data: Sequence[Dict[str, Any]]) -> List[APIModel]:
        """
        Load available models from test case data and convert them to APIModel objects.

        This mimics the real scenario where APIModel has:
        - path: API path (e.g., '/users')
        - files: list of 'file_path - summary' strings

        Args:
            available_models_data: List of dicts with 'path' and 'files' keys

        Returns:
            List of APIModel objects representing available models
        """
        available_models: List[APIModel] = []

        for model_data in available_models_data:
            api_path = model_data.get("path", "")
            files = model_data.get("files", [])

            api_model = APIModel(path=api_path, files=files)
            available_models.append(api_model)
            self.logger.debug(f"Loaded available model for path {api_path}: {len(files)} file(s)")

        return available_models
