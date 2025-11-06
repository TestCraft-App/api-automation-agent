"""Service for running evaluations on LLMService generation methods."""

import os
import tempfile
from typing import List, Optional

from src.ai_tools.models.file_spec import FileSpec
from src.configuration.config import Config
from src.models.generated_model import GeneratedModel
from src.services.file_service import FileService
from src.services.llm_service import LLMService
from src.utils.logger import Logger
from evaluations.models.evaluation_dataset import (
    EvaluationDataset,
    EvaluationResult,
    EvaluationRunResult,
    EvaluationTestCase,
    ModelGradeResult,
)
from evaluations.services.model_grader import ModelGrader


class EvaluationRunner:
    """Service for running evaluations on LLMService methods."""

    def __init__(
        self,
        config: Config,
        llm_service: LLMService,
        file_service: FileService,
        test_data_folder: str,
        model_grader: Optional[ModelGrader] = None,
    ):
        """
        Initialize the Evaluation Runner.

        Args:
            config: Configuration object
            llm_service: LLMService instance for generating tests
            file_service: FileService instance for file operations
            test_data_folder: Path to folder containing test data (API definition files)
            model_grader: Optional ModelGrader instance. If not provided, will create one.
        """
        self.config = config
        self.llm_service = llm_service
        self.file_service = file_service
        self.test_data_folder = test_data_folder
        self.logger = Logger.get_logger(__name__)
        self.model_grader = model_grader or ModelGrader(config)

    def _load_api_definition(self, api_definition_file: str) -> Optional[str]:
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

    def _remove_test_id_from_filename(self, path: str, test_id: str) -> str:
        """
        Remove test_id prefix from the filename in a file path.

        Args:
            path: File path where test_id prefixes the filename (e.g., "requests/test_001_UserModel.ts")
            test_id: Test identifier to remove from filename

        Returns:
            Path with test_id prefix removed from filename (e.g., "requests/UserModel.ts")
        """
        import os

        directory = os.path.dirname(path)
        filename = os.path.basename(path)

        if filename.startswith(f"{test_id}_"):
            filename = filename[len(f"{test_id}_") :]

        if directory:
            return os.path.join(directory, filename)
        return filename

    def _load_models(self, model_files: List[str], test_id: str) -> List[GeneratedModel]:
        """
        Load model files from the models folder within the test data folder
        and convert them to GeneratedModel objects.
        The test_id prefix is removed from filenames and 'src/models/' is prepended.

        Args:
            model_files: List of model file paths relative to the models folder
                (e.g., "requests/test_001_UserModel.ts")
            test_id: Test identifier used as prefix in filenames

        Returns:
            List of GeneratedModel objects with paths like "src/models/requests/UserModel.ts"
        """
        models_folder = os.path.join(self.test_data_folder, "models")
        generated_models = []
        for model_file in model_files:
            file_path = os.path.join(models_folder, model_file)
            if not os.path.exists(file_path):
                self.logger.warning(f"Model file not found: {file_path}, skipping")
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                clean_path = self._remove_test_id_from_filename(model_file, test_id)
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

    def _evaluate_generated_files(
        self, generated_files: List[FileSpec], evaluation_criteria: str
    ) -> Optional[ModelGradeResult]:
        """
        Evaluate generated files against criteria using model grading.

        Args:
            generated_files: List of generated FileSpec objects
            evaluation_criteria: Criteria to evaluate against

        Returns:
            ModelGradeResult if evaluation succeeded, None otherwise
        """
        if not generated_files:
            return ModelGradeResult(
                passed=False,
                score=0.0,
                feedback="No files were generated",
                reasoning="The generate_first_test method returned an empty list",
            )

        first_file = generated_files[0]
        file_content = first_file.fileContent

        return self.model_grader.grade(file_content, evaluation_criteria)

    def evaluate_generate_first_test(self, test_case: EvaluationTestCase) -> EvaluationResult:
        """
        Evaluate the generate_first_test method for a single test case.

        Args:
            test_case: The test case to evaluate

        Returns:
            EvaluationResult with the evaluation outcome
        """
        self.logger.info(f"Evaluating test case: {test_case.test_id} - {test_case.name}")

        api_definition_content = self._load_api_definition(test_case.api_definition_file)
        if not api_definition_content:
            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status="ERROR",
                error_message=f"Failed to load API definition file: {test_case.api_definition_file}",
                evaluation_criteria=test_case.evaluation_criteria,
            )

        models = self._load_models(test_case.model_files, test_case.test_id)
        if not models:
            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status="ERROR",
                error_message=f"Failed to load model files: {', '.join(test_case.model_files)}",
                evaluation_criteria=test_case.evaluation_criteria,
            )

        original_destination = self.config.destination_folder
        with tempfile.TemporaryDirectory(prefix=f"eval_{test_case.name}_") as temp_dir:
            try:
                self.config.destination_folder = temp_dir

                generated_files = self.llm_service.generate_first_test(api_definition_content, models)

                if not generated_files:
                    return EvaluationResult(
                        test_id=test_case.test_id,
                        test_case_name=test_case.name,
                        api_definition_file=test_case.api_definition_file,
                        status="FAILED",
                        error_message="No files were generated",
                        evaluation_criteria=test_case.evaluation_criteria,
                    )

                grade_result = self._evaluate_generated_files(generated_files, test_case.evaluation_criteria)

                if grade_result and grade_result.passed:
                    status = "SUCCESS"
                else:
                    status = "FAILED"

                return EvaluationResult(
                    test_id=test_case.test_id,
                    test_case_name=test_case.name,
                    api_definition_file=test_case.api_definition_file,
                    status=status,
                    generated_files=[f.path for f in generated_files],
                    grade_result=grade_result,
                    evaluation_criteria=test_case.evaluation_criteria,
                )

            except Exception as e:
                self.logger.error(
                    f"Error during evaluation of test case {test_case.test_id} - {test_case.name}: {e}",
                    exc_info=True,
                )
                return EvaluationResult(
                    test_id=test_case.test_id,
                    test_case_name=test_case.name,
                    api_definition_file=test_case.api_definition_file,
                    status="ERROR",
                    error_message=str(e),
                    evaluation_criteria=test_case.evaluation_criteria,
                )
            finally:
                self.config.destination_folder = original_destination

    def run_evaluation(self, dataset: EvaluationDataset) -> EvaluationRunResult:
        """
        Run evaluation on all test cases in a dataset.

        Args:
            dataset: The evaluation dataset to run

        Returns:
            EvaluationRunResult with aggregated results
        """
        self.logger.info(f"Starting evaluation run for dataset: {dataset.dataset_name}")
        self.logger.info(f"Number of test cases: {len(dataset.test_cases)}")

        results: List[EvaluationResult] = []
        passed_count = 0
        failed_count = 0
        error_count = 0

        for test_case in dataset.test_cases:
            result = self.evaluate_generate_first_test(test_case)
            results.append(result)

            if result.status == "SUCCESS":
                passed_count += 1
            elif result.status == "FAILED":
                failed_count += 1
            else:
                error_count += 1

            self.logger.info(f"Test case '{test_case.name}': {result.status}")

        self.logger.info(
            f"Evaluation run completed. Passed: {passed_count}, Failed: {failed_count}, Errors: {error_count}"
        )

        return EvaluationRunResult(
            dataset_name=dataset.dataset_name,
            total_test_cases=len(dataset.test_cases),
            passed_count=passed_count,
            failed_count=failed_count,
            error_count=error_count,
            results=results,
        )
