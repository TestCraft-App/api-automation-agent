"""Service for running evaluations on LLMService generation methods."""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional

from src.configuration.config import Config
from src.services.file_service import FileService
from src.services.llm_service import LLMService
from src.utils.logger import Logger
from evaluations.models.evaluation_dataset import (
    EvaluationDataset,
    EvaluationResult,
    EvaluationRunResult,
    EvaluationTestCase,
)
from evaluations.services.evaluation_data_loader import EvaluationDataLoader
from evaluations.services.evaluation_file_writer import EvaluationFileWriter
from evaluations.services.model_grader import ModelGrader
from evaluations.services.evaluators.base_evaluator import BaseEvaluator
from evaluations.services.evaluators.first_test_evaluator import FirstTestEvaluator
from evaluations.services.evaluators.models_evaluator import ModelsEvaluator
from evaluations.services.evaluators.additional_tests_evaluator import AdditionalTestsEvaluator
from evaluations.services.evaluators.additional_models_evaluator import AdditionalModelsEvaluator


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
            grader_config: Optional Config object for the grader model.
                If not provided, uses config.
            model_grader: Optional ModelGrader instance. If not provided, will create one.
            max_workers: Maximum number of parallel workers for test execution (default: 4)
        """
        self.config = config
        self.llm_service = llm_service
        self.file_service = file_service
        self.test_data_folder = test_data_folder
        self.logger = Logger.get_logger(__name__)
        self.max_workers = max_workers

        grader_config_to_use = grader_config or config
        self.model_grader = model_grader or ModelGrader(grader_config_to_use)
        self.data_loader = EvaluationDataLoader(test_data_folder)
        self.file_writer = EvaluationFileWriter()

        self._evaluators: List[BaseEvaluator] = self._create_evaluators()

    def _create_evaluators(self) -> List[BaseEvaluator]:
        """Create and return all available evaluators."""
        evaluator_classes = [
            FirstTestEvaluator,
            ModelsEvaluator,
            AdditionalTestsEvaluator,
            AdditionalModelsEvaluator,
        ]

        return [
            evaluator_class(
                config=self.config,
                llm_service=self.llm_service,
                data_loader=self.data_loader,
                file_writer=self.file_writer,
                model_grader=self.model_grader,
            )
            for evaluator_class in evaluator_classes
        ]

    def register_evaluator(self, evaluator: BaseEvaluator) -> None:
        """
        Register a custom evaluator.

        Args:
            evaluator: An evaluator instance to register
        """
        self._evaluators.append(evaluator)

    def _get_evaluator_for_case_type(self, case_type: str) -> Optional[BaseEvaluator]:
        """Find an evaluator that can handle the given case type."""
        for evaluator in self._evaluators:
            if evaluator.can_handle(case_type):
                return evaluator
        return None

    def _create_error_result(self, test_case: EvaluationTestCase, message: str) -> EvaluationResult:
        """Create an error result for a test case."""
        return EvaluationResult(
            test_id=test_case.test_id,
            test_case_name=test_case.name,
            api_definition_file=test_case.api_definition_file,
            status="ERROR",
            error_message=message,
            evaluation_criteria=test_case.evaluation_criteria,
        )

    def _evaluate_single_test_case(
        self, test_case: EvaluationTestCase, base_output_dir: str
    ) -> EvaluationResult:
        """
        Evaluate a single test case by delegating to the appropriate evaluator.

        Args:
            test_case: The test case to evaluate
            base_output_dir: Base directory for output files

        Returns:
            EvaluationResult for the test case
        """
        test_output_dir = os.path.join(base_output_dir, test_case.test_id)

        evaluator = self._get_evaluator_for_case_type(test_case.case_type)
        if not evaluator:
            self.logger.error(
                "No evaluator found for case type '%s' (test %s)",
                test_case.case_type,
                test_case.test_id,
            )
            return self._create_error_result(test_case, f"Unknown evaluation type '{test_case.case_type}'")

        result = evaluator.evaluate(test_case, test_output_dir)
        self.logger.info(f"Test case '{test_case.name}': {result.status}")
        return result

    def run_evaluation(
        self, dataset: EvaluationDataset, test_ids_filter: Optional[List[str]] = None
    ) -> EvaluationRunResult:
        """
        Run evaluation on all test cases in a dataset.

        Args:
            dataset: The evaluation dataset to run
            test_ids_filter: Optional list of test IDs to filter by. If provided,
                only test cases with matching test_id will be evaluated.

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
                        self._create_error_result(
                            test_case,
                            f"Unexpected error during parallel execution: {str(e)}",
                        )
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
