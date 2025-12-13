"""Service for running evaluations on LLMService generation methods."""

import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, List, Literal, Optional, Sequence

from src.ai_tools.models.file_spec import FileSpec
from src.configuration.config import Config
from src.configuration.data_sources import DataSource
from src.processors.postman.postman_utils import PostmanUtils
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
from evaluations.services.evaluation_data_loader import EvaluationDataLoader
from evaluations.services.evaluation_file_writer import EvaluationFileWriter
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
        self.data_loader = EvaluationDataLoader(test_data_folder)
        self.file_writer = EvaluationFileWriter()

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _error_result(
        self,
        test_case: EvaluationTestCase,
        message: str,
        status: Literal["ERROR", "NOT_EVALUATED"] = "ERROR",
    ) -> EvaluationResult:
        """Create an error or not-evaluated result for a test case."""
        return EvaluationResult(
            test_id=test_case.test_id,
            test_case_name=test_case.name,
            api_definition_file=test_case.api_definition_file,
            status=status,
            error_message=message,
            evaluation_criteria=test_case.evaluation_criteria,
        )

    def _setup_output_dir(self, output_dir: str) -> None:
        """Setup output directory, clearing it if it exists."""
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

    @contextmanager
    def _temporary_config(self, **overrides: Any) -> Generator[None, None, None]:
        """Context manager for temporarily overriding config values."""
        originals = {k: getattr(self.config, k) for k in overrides}
        for k, v in overrides.items():
            setattr(self.config, k, v)
        try:
            yield
        finally:
            for k, v in originals.items():
                setattr(self.config, k, v)

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

    # -------------------------------------------------------------------------
    # Evaluation Methods
    # -------------------------------------------------------------------------

    def evaluate_generate_first_test(
        self,
        test_case: EvaluationTestCase,
        output_dir: str,
        api_definition_content: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate the generate_first_test method for a single test case.

        Args:
            test_case: The test case to evaluate
            output_dir: Destination directory where generated files should be written
            api_definition_content: Optional pre-loaded/preprocessed API definition content.
                If not provided, loads from test_case.api_definition_file.

        Returns:
            EvaluationResult with the evaluation outcome
        """
        self.logger.info(f"Evaluating test case: {test_case.test_id} - {test_case.name}")

        if api_definition_content is None:
            api_definition_content = self.data_loader.load_api_definition(test_case.api_definition_file)
        if not api_definition_content:
            return self._error_result(
                test_case, f"Failed to load API definition file: {test_case.api_definition_file}"
            )

        models = self.data_loader.load_models(test_case.model_files)
        if not models:
            return self._error_result(
                test_case, f"Failed to load model files: {', '.join(test_case.model_files)}"
            )

        self._setup_output_dir(output_dir)

        try:
            with self._temporary_config(destination_folder=output_dir):
                generated_files = self.llm_service.generate_first_test(api_definition_content, models)

                if not generated_files:
                    return self._error_result(test_case, "No files were generated", status="NOT_EVALUATED")

                saved_paths = self.file_writer.save_generated_files(generated_files, output_dir)
                grade_result = self._evaluate_generated_files(generated_files, test_case.evaluation_criteria)

                return EvaluationResult(
                    test_id=test_case.test_id,
                    test_case_name=test_case.name,
                    api_definition_file=test_case.api_definition_file,
                    status="GRADED" if grade_result else "NOT_EVALUATED",
                    generated_files=saved_paths,
                    grade_result=grade_result,
                    evaluation_criteria=test_case.evaluation_criteria,
                )

        except Exception as e:
            self.logger.error(
                f"Error during evaluation of test case {test_case.test_id} - {test_case.name}: {e}",
                exc_info=True,
            )
            return self._error_result(test_case, str(e))

    def _preprocess_postman_definition(self, raw_content: str) -> Optional[str]:
        """
        Preprocess a raw Postman collection into the format expected by llm_service.

        In real scenarios, PostmanProcessor.get_api_verb_content() returns a JSON with:
        - file_path, root_path, full_path, verb, body, prerequest, script, name

        This method extracts the first request from the collection and formats it
        the same way the real processor does.

        Args:
            raw_content: Raw Postman collection JSON string

        Returns:
            Preprocessed JSON string in the format expected by generate_first_test,
            or None if parsing fails
        """
        try:
            data = json.loads(raw_content)
            requests = PostmanUtils.extract_requests(data, prefixes=self.config.prefixes)

            if not requests:
                self.logger.error("No requests found in Postman collection")
                return None

            api_verb = requests[0]

            return json.dumps(
                {
                    "file_path": api_verb.file_path,
                    "root_path": api_verb.root_path,
                    "full_path": api_verb.full_path,
                    "verb": api_verb.verb,
                    "body": api_verb.body,
                    "prerequest": api_verb.prerequest,
                    "script": api_verb.script,
                    "name": api_verb.name,
                }
            )
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Postman collection: {e}")
            return None

    def evaluate_generate_first_test_postman(
        self, test_case: EvaluationTestCase, output_dir: str
    ) -> EvaluationResult:
        """
        Evaluate the generate_first_test method for a Postman-based test case.

        This method preprocesses the Postman collection to match the format that
        llm_service.generate_first_test receives in real scenarios (via
        PostmanProcessor.get_api_verb_content()), then delegates to evaluate_generate_first_test.

        Args:
            test_case: The test case to evaluate
            output_dir: Destination directory where generated files should be written

        Returns:
            EvaluationResult with the evaluation outcome
        """
        raw_definition = self.data_loader.load_api_definition(test_case.api_definition_file)
        if not raw_definition:
            return self._error_result(
                test_case, f"Failed to load API definition file: {test_case.api_definition_file}"
            )

        api_definition_content = self._preprocess_postman_definition(raw_definition)
        if not api_definition_content:
            return self._error_result(test_case, "Failed to preprocess Postman collection")

        with self._temporary_config(data_source=DataSource.POSTMAN):
            return self.evaluate_generate_first_test(test_case, output_dir, api_definition_content)

    def evaluate_generate_models(self, test_case: EvaluationTestCase, output_dir: str) -> EvaluationResult:
        """Evaluate the generate_models method for a single test case."""
        self.logger.info(f"Evaluating models for test case: {test_case.test_id} - {test_case.name}")

        api_definition_content = self.data_loader.load_api_definition(test_case.api_definition_file)
        if not api_definition_content:
            return self._error_result(
                test_case, f"Failed to load API definition file: {test_case.api_definition_file}"
            )

        self._setup_output_dir(output_dir)

        try:
            with self._temporary_config(destination_folder=output_dir):
                generated_model_specs = self.llm_service.generate_models(api_definition_content)

                if not generated_model_specs:
                    return self._error_result(test_case, "No models were generated", status="NOT_EVALUATED")

                file_specs = [
                    FileSpec(path=model_spec.path, fileContent=model_spec.fileContent)
                    for model_spec in generated_model_specs
                ]

                saved_paths = self.file_writer.save_generated_files(file_specs, output_dir)
                grade_result = self._evaluate_generated_files(file_specs, test_case.evaluation_criteria)

                return EvaluationResult(
                    test_id=test_case.test_id,
                    test_case_name=test_case.name,
                    api_definition_file=test_case.api_definition_file,
                    status="GRADED" if grade_result else "NOT_EVALUATED",
                    generated_files=saved_paths,
                    grade_result=grade_result,
                    evaluation_criteria=test_case.evaluation_criteria,
                )

        except Exception as e:
            self.logger.error(
                f"Error during model evaluation of test case {test_case.test_id} - {test_case.name}: {e}",
                exc_info=True,
            )
            return self._error_result(test_case, str(e))

    def evaluate_generate_additional_tests(
        self, test_case: EvaluationTestCase, output_dir: str
    ) -> EvaluationResult:
        """Evaluate the generate_additional_tests method for a single test case."""
        self.logger.info(
            "Evaluating additional tests for test case: %s - %s",
            test_case.test_id,
            test_case.name,
        )

        api_definition_content = self.data_loader.load_api_definition(test_case.api_definition_file)
        if not api_definition_content:
            return self._error_result(
                test_case, f"Failed to load API definition file: {test_case.api_definition_file}"
            )

        models = self.data_loader.load_models(test_case.model_files)
        if not models:
            return self._error_result(
                test_case,
                "No models were available to generate additional tests",
                status="NOT_EVALUATED",
            )

        first_test = self.data_loader.load_first_test_file(test_case.first_test_file)
        if not first_test:
            return self._error_result(
                test_case,
                "First test file could not be loaded for generating additional tests",
                status="NOT_EVALUATED",
            )

        self._setup_output_dir(output_dir)

        try:
            with self._temporary_config(destination_folder=output_dir):
                generated_files = self.llm_service.generate_additional_tests(
                    tests=[first_test],
                    models=models,
                    definition_content=api_definition_content,
                )

                if not generated_files:
                    return self._error_result(
                        test_case, "No additional tests were generated", status="NOT_EVALUATED"
                    )

                saved_paths = self.file_writer.save_generated_files(generated_files, output_dir)
                grade_result = self._evaluate_generated_files(generated_files, test_case.evaluation_criteria)

                return EvaluationResult(
                    test_id=test_case.test_id,
                    test_case_name=test_case.name,
                    api_definition_file=test_case.api_definition_file,
                    status="GRADED" if grade_result else "NOT_EVALUATED",
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
            return self._error_result(test_case, str(e))

    def evaluate_get_additional_models(self, test_case: EvaluationTestCase) -> EvaluationResult:
        """
        Evaluate the get_additional_models method for a single test case.
        Uses assertion-based grading instead of LLM grading.
        """
        self.logger.info(
            "Evaluating get_additional_models for test case: %s - %s",
            test_case.test_id,
            test_case.name,
        )

        relevant_models = self.data_loader.load_models(test_case.model_files)
        if not relevant_models and test_case.model_files:
            return self._error_result(
                test_case, f"Failed to load model files: {', '.join(test_case.model_files)}"
            )

        available_models = self.data_loader.load_available_models(test_case.available_models)
        if not available_models and test_case.available_models:
            return self._error_result(test_case, "Failed to load available models from test case")

        try:
            mock_tool = MockFileReadingTool()
            result_files = self.llm_service.get_additional_models(
                relevant_models, available_models, file_reading_tool=mock_tool
            )

            actual_paths = sorted([f.path for f in result_files])

            expected_paths = sorted(
                [
                    (
                        f"src/models/{self.data_loader.normalize_dataset_path(p)}"
                        if not p.startswith("src/")
                        else p
                    )
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
            return self._error_result(test_case, str(e))

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
        elif test_case.case_type == "generate_first_test_postman":
            result = self.evaluate_generate_first_test_postman(test_case, test_output_dir)
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
            result = self._error_result(test_case, f"Unknown evaluation type '{test_case.case_type}'")

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
                    results.append(
                        self._error_result(test_case, f"Unexpected error during parallel execution: {str(e)}")
                    )
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
