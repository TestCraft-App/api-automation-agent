"""Service for running evaluations on LLMService generation methods."""

import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from src.ai_tools.models.file_spec import FileSpec
from src.configuration.config import Config
from src.models.api_model import APIModel
from src.models.generated_model import GeneratedModel
from src.services.file_service import FileService
from src.services.llm_service import LLMService
from src.utils.logger import Logger
from evaluations.models.evaluation_dataset import (
    EvaluationCriterionResult,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRunResult,
    EvaluationTestCase,
    ModelGradeResult,
)
from evaluations.services.model_grader import ModelGrader
from evaluations.services.mock_file_reading_tool import MockFileReadingTool


class EvaluationRunner:
    """Service for running evaluations on LLMService methods."""

    def __init__(
        self,
        config: Config,
        llm_service: LLMService,
        file_service: FileService,
        test_data_folder: str,
        grader_config: Optional[Config] = None,
        model_grader: Optional[ModelGrader] = None,
        max_workers: int = 4,
    ):
        """
        Initialize the Evaluation Runner.

        Args:
            config: Configuration object for the tested model
            llm_service: LLMService instance for generating tests
            file_service: FileService instance for file operations
            test_data_folder: Path to folder containing test data (API definition files)
            grader_config: Optional Config object for the grader model. If not provided, uses config.
            model_grader: Optional ModelGrader instance. If not provided, will create one.
            max_workers: Maximum number of parallel workers for test execution (default: 4)
        """
        self.config = config
        self.llm_service = llm_service
        self.file_service = file_service
        self.test_data_folder = test_data_folder
        self.logger = Logger.get_logger(__name__)
        grader_config_to_use = grader_config or config
        self.model_grader = model_grader or ModelGrader(grader_config_to_use)
        self.max_workers = max_workers

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

    def _normalize_dataset_path(self, path: str) -> str:
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

    def _load_models(self, model_files: Sequence[str]) -> List[GeneratedModel]:
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

                clean_path = self._normalize_dataset_path(model_file)
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

    def _load_first_test_file(self, test_file: Optional[str]) -> Optional[FileSpec]:
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

            clean_path = self._normalize_dataset_path(test_file)
            final_path = f"src/tests/{clean_path}"
            self.logger.debug(f"Loaded first test file: {test_file} -> {final_path}")
            return FileSpec(path=final_path, fileContent=file_content)
        except Exception as e:
            self.logger.error(f"Error reading first test file {file_path}: {e}")
            return None

    def _save_generated_files(self, generated_files: List[FileSpec], output_dir: str) -> List[str]:
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

    def _evaluate_generated_files(
        self, generated_files: List[FileSpec], evaluation_criteria: Sequence[str]
    ) -> Optional[ModelGradeResult]:
        """
        Evaluate generated files against criteria using model grading.

        Args:
            generated_files: List of generated FileSpec objects
            evaluation_criteria: Ordered list of criteria to evaluate against

        Returns:
            ModelGradeResult if evaluation succeeded, None otherwise
        """
        if not generated_files:
            return ModelGradeResult(
                score=0.0,
                evaluation=[
                    EvaluationCriterionResult(
                        criteria="File generation",
                        met=False,
                        details="No files were generated for evaluation",
                    )
                ],
                reasoning="The generate_first_test method returned an empty list",
            )

        combined_content = "\n\n".join(
            f"// File: {file.path}\n{file.fileContent}" for file in generated_files
        )

        return self.model_grader.grade(combined_content, evaluation_criteria)

    def evaluate_generate_first_test(
        self, test_case: EvaluationTestCase, output_dir: str
    ) -> EvaluationResult:
        """
        Evaluate the generate_first_test method for a single test case.

        Args:
            test_case: The test case to evaluate
            output_dir: Destination directory where generated files should be written

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

        models = self._load_models(test_case.model_files)
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
        os.makedirs(output_dir, exist_ok=True)
        if os.listdir(output_dir):
            shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)

        try:
            self.config.destination_folder = output_dir

            generated_files = self.llm_service.generate_first_test(api_definition_content, models)

            if not generated_files:
                return EvaluationResult(
                    test_id=test_case.test_id,
                    test_case_name=test_case.name,
                    api_definition_file=test_case.api_definition_file,
                    status="NOT_EVALUATED",
                    error_message="No files were generated",
                    evaluation_criteria=test_case.evaluation_criteria,
                )

            saved_paths = self._save_generated_files(generated_files, output_dir)
            grade_result = self._evaluate_generated_files(generated_files, test_case.evaluation_criteria)

            status = "GRADED" if grade_result else "NOT_EVALUATED"

            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status=status,
                generated_files=saved_paths,
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

    def evaluate_generate_models(self, test_case: EvaluationTestCase, output_dir: str) -> EvaluationResult:
        """
        Evaluate the generate_models method for a single test case.
        """
        self.logger.info(f"Evaluating models for test case: {test_case.test_id} - {test_case.name}")

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

        original_destination = self.config.destination_folder
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        try:
            self.config.destination_folder = output_dir

            generated_model_specs = self.llm_service.generate_models(api_definition_content)

            if not generated_model_specs:
                return EvaluationResult(
                    test_id=test_case.test_id,
                    test_case_name=test_case.name,
                    api_definition_file=test_case.api_definition_file,
                    status="NOT_EVALUATED",
                    error_message="No models were generated",
                    evaluation_criteria=test_case.evaluation_criteria,
                )

            file_specs = [
                FileSpec(path=model_spec.path, fileContent=model_spec.fileContent)
                for model_spec in generated_model_specs
            ]

            saved_paths = self._save_generated_files(file_specs, output_dir)
            grade_result = self._evaluate_generated_files(file_specs, test_case.evaluation_criteria)
            status = "GRADED" if grade_result else "NOT_EVALUATED"

            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status=status,
                generated_files=saved_paths,
                grade_result=grade_result,
                evaluation_criteria=test_case.evaluation_criteria,
            )

        except Exception as e:
            self.logger.error(
                f"Error during model evaluation of test case {test_case.test_id} - {test_case.name}: {e}",
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

    def evaluate_generate_additional_tests(
        self, test_case: EvaluationTestCase, output_dir: str
    ) -> EvaluationResult:
        """
        Evaluate the generate_additional_tests method for a single test case.
        """
        self.logger.info(
            "Evaluating additional tests for test case: %s - %s",
            test_case.test_id,
            test_case.name,
        )

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

        models = self._load_models(test_case.model_files)
        if not models:
            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status="NOT_EVALUATED",
                error_message="No models were available to generate additional tests",
                evaluation_criteria=test_case.evaluation_criteria,
            )

        first_test = self._load_first_test_file(test_case.first_test_file)
        if not first_test:
            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status="NOT_EVALUATED",
                error_message="First test file could not be loaded for generating additional tests",
                evaluation_criteria=test_case.evaluation_criteria,
            )

        original_destination = self.config.destination_folder
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        try:
            self.config.destination_folder = output_dir

            generated_files = self.llm_service.generate_additional_tests(
                tests=[first_test],
                models=models,
                definition_content=api_definition_content,
            )

            if not generated_files:
                return EvaluationResult(
                    test_id=test_case.test_id,
                    test_case_name=test_case.name,
                    api_definition_file=test_case.api_definition_file,
                    status="NOT_EVALUATED",
                    error_message="No additional tests were generated",
                    evaluation_criteria=test_case.evaluation_criteria,
                )

            saved_paths = self._save_generated_files(generated_files, output_dir)
            grade_result = self._evaluate_generated_files(generated_files, test_case.evaluation_criteria)
            status = "GRADED" if grade_result else "NOT_EVALUATED"

            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status=status,
                generated_files=saved_paths,
                grade_result=grade_result,
                evaluation_criteria=test_case.evaluation_criteria,
            )

        except Exception as e:
            self.logger.error(
                "Error during additional test evaluation of test case %s - %s: %s",
                test_case.test_id,
                test_case.name,
                e,
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

    def _load_available_models_from_test_case(
        self, available_models_data: Sequence[Dict[str, Any]]
    ) -> List[APIModel]:
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

    def evaluate_get_additional_models(self, test_case: EvaluationTestCase) -> EvaluationResult:
        """
        Evaluate the get_additional_models method for a single test case.
        Uses assertion-based grading instead of LLM grading.

        Args:
            test_case: The test case to evaluate

        Returns:
            EvaluationResult with the evaluation outcome
        """
        self.logger.info(
            "Evaluating get_additional_models for test case: %s - %s",
            test_case.test_id,
            test_case.name,
        )

        relevant_models = self._load_models(test_case.model_files)
        if not relevant_models and test_case.model_files:
            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status="ERROR",
                error_message=f"Failed to load model files: {', '.join(test_case.model_files)}",
                evaluation_criteria=test_case.evaluation_criteria,
            )

        available_models = self._load_available_models_from_test_case(test_case.available_models)
        if not available_models and test_case.available_models:
            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status="ERROR",
                error_message="Failed to load available models from test case",
                evaluation_criteria=test_case.evaluation_criteria,
            )

        try:
            mock_tool = MockFileReadingTool()
            result_files = self.llm_service.get_additional_models(
                relevant_models, available_models, file_reading_tool=mock_tool
            )

            actual_paths = sorted([f.path for f in result_files])

            expected_paths = sorted(
                [
                    f"src/models/{self._normalize_dataset_path(p)}" if not p.startswith("src/") else p
                    for p in test_case.expected_files
                ]
            )

            evaluation_results: List[EvaluationCriterionResult] = []

            missing_files = set(expected_paths) - set(actual_paths)
            extra_files = set(actual_paths) - set(expected_paths)

            # Criterion 1: All expected files are returned
            expected_met = len(missing_files) == 0
            evaluation_results.append(
                EvaluationCriterionResult(
                    criteria="All expected files are returned",
                    met=expected_met,
                    details=(
                        "All expected files were correctly identified"
                        if expected_met
                        else f"Missing files: {list(missing_files)}"
                    ),
                )
            )

            # Criterion 2: No unnecessary files are returned
            no_extra_met = len(extra_files) == 0
            evaluation_results.append(
                EvaluationCriterionResult(
                    criteria="No unnecessary files are returned",
                    met=no_extra_met,
                    details=(
                        "No unnecessary files were read"
                        if no_extra_met
                        else f"Extra files returned: {list(extra_files)}"
                    ),
                )
            )

            criteria_met = sum(1 for r in evaluation_results if r.met)
            score = criteria_met / len(evaluation_results) if evaluation_results else 0.0

            grade_result = ModelGradeResult(
                score=score,
                evaluation=evaluation_results,
                reasoning=(
                    f"Expected {len(expected_paths)} file(s), got {len(actual_paths)}. "
                    f"Missing: {len(missing_files)}, Extra: {len(extra_files)}."
                ),
            )

            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status="GRADED",
                generated_files=actual_paths,
                grade_result=grade_result,
                evaluation_criteria=test_case.evaluation_criteria,
            )

        except Exception as e:
            self.logger.error(
                "Error during get_additional_models evaluation of test case %s - %s: %s",
                test_case.test_id,
                test_case.name,
                e,
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

    def _evaluate_single_test_case(
        self, test_case: EvaluationTestCase, base_output_dir: str
    ) -> EvaluationResult:
        """
        Evaluate a single test case based on its type.

        Args:
            test_case: The test case to evaluate
            base_output_dir: Base directory for output files

        Returns:
            EvaluationResult for the test case
        """
        test_output_dir = os.path.join(base_output_dir, test_case.test_id)

        if test_case.case_type == "generate_models":
            result = self.evaluate_generate_models(test_case, test_output_dir)
        elif test_case.case_type == "generate_first_test":
            result = self.evaluate_generate_first_test(test_case, test_output_dir)
        elif test_case.case_type == "generate_additional_tests":
            result = self.evaluate_generate_additional_tests(test_case, test_output_dir)
        elif test_case.case_type == "get_additional_models":
            result = self.evaluate_get_additional_models(test_case)
        else:
            self.logger.error(
                "Unknown evaluation type '%s' for test %s",
                test_case.case_type,
                test_case.test_id,
            )
            result = EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status="ERROR",
                error_message=f"Unknown evaluation type '{test_case.case_type}'",
                evaluation_criteria=test_case.evaluation_criteria,
            )

        self.logger.info(f"Test case '{test_case.name}': {result.status}")
        return result

    def run_evaluation(
        self, dataset: EvaluationDataset, test_ids_filter: Optional[List[str]] = None
    ) -> EvaluationRunResult:
        """
        Run evaluation on all test cases in a dataset.

        Args:
            dataset: The evaluation dataset to run
            test_ids_filter: Optional list of test IDs to filter by. If provided, only test cases
                           with matching test_id will be evaluated.

        Returns:
            EvaluationRunResult with aggregated results
        """
        test_cases = dataset.test_cases
        if test_ids_filter:
            test_cases = [tc for tc in dataset.test_cases if tc.test_id in test_ids_filter]
            if not test_cases:
                self.logger.warning(
                    f"No test cases found matching filter: {test_ids_filter}. "
                    f"Available test IDs: {[tc.test_id for tc in dataset.test_cases]}"
                )
            else:
                filtered_ids = [tc.test_id for tc in test_cases]
                self.logger.info(f"Filtered to {len(test_cases)} test case(s): {filtered_ids}")

        self.logger.info(f"Starting evaluation run for dataset: {dataset.dataset_name}")
        print(f"Evaluating model: {self.config.model.name} ({self.config.model.value})")
        self.logger.info(f"Number of test cases: {len(test_cases)}\n")

        usage_before = self.llm_service.get_aggregated_usage_metadata().model_copy(deep=True)

        results: List[EvaluationResult] = []
        graded_count = 0
        not_evaluated_count = 0
        error_count = 0
        scores: List[float] = []

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output_dir = os.path.join(
            "evaluations",
            "reports",
            "generated-files",
            f"{dataset.dataset_name}_{timestamp}",
        )
        os.makedirs(base_output_dir, exist_ok=True)

        self.logger.info(f"Running test cases in parallel with {self.max_workers} workers")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_test = {
                executor.submit(self._evaluate_single_test_case, test_case, base_output_dir): test_case
                for test_case in test_cases
            }

            for future in as_completed(future_to_test):
                test_case = future_to_test[future]
                try:
                    result = future.result()
                    results.append(result)

                    if result.status == "GRADED":
                        graded_count += 1
                    elif result.status == "NOT_EVALUATED":
                        not_evaluated_count += 1
                    else:
                        error_count += 1

                    if result.grade_result and result.grade_result.score is not None:
                        scores.append(result.grade_result.score)

                except Exception as e:
                    self.logger.error(
                        f"Unexpected error processing test case {test_case.test_id}: {e}",
                        exc_info=True,
                    )
                    error_result = EvaluationResult(
                        test_id=test_case.test_id,
                        test_case_name=test_case.name,
                        api_definition_file=test_case.api_definition_file,
                        status="ERROR",
                        error_message=f"Unexpected error during parallel execution: {str(e)}",
                        evaluation_criteria=test_case.evaluation_criteria,
                    )
                    results.append(error_result)
                    error_count += 1

        self.logger.info(
            "Evaluation run completed. Graded: %s, Not Evaluated: %s, Errors: %s",
            graded_count,
            not_evaluated_count,
            error_count,
        )

        average_score = sum(scores) / len(scores) if scores else None

        usage_after = self.llm_service.get_aggregated_usage_metadata()
        total_input_tokens = usage_after.total_input_tokens - usage_before.total_input_tokens
        total_output_tokens = usage_after.total_output_tokens - usage_before.total_output_tokens
        total_cost = usage_after.total_cost - usage_before.total_cost

        return EvaluationRunResult(
            dataset_name=dataset.dataset_name,
            llm_model=self.config.model.value,
            total_test_cases=len(test_cases),
            graded_count=graded_count,
            not_evaluated_count=not_evaluated_count,
            error_count=error_count,
            total_input_tokens=max(total_input_tokens, 0),
            total_output_tokens=max(total_output_tokens, 0),
            total_cost=max(total_cost, 0.0),
            average_score=average_score,
            generated_files_path=os.path.abspath(base_output_dir),
            results=results,
        )
