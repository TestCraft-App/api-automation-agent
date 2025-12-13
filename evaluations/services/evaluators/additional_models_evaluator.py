"""Evaluator for get_additional_models."""

from typing import List

from evaluations.models.evaluation_dataset import (
    EvaluationCriterionResult,
    EvaluationResult,
    EvaluationTestCase,
    ModelGradeResult,
)
from evaluations.services.evaluators.base_evaluator import BaseEvaluator
from evaluations.services.mock_file_reading_tool import MockFileReadingTool


class AdditionalModelsEvaluator(BaseEvaluator):
    """Evaluator for get_additional_models method (uses assertion-based grading)."""

    supported_case_types = ["get_additional_models"]

    def evaluate(self, test_case: EvaluationTestCase, output_dir: str) -> EvaluationResult:
        """
        Evaluate the get_additional_models method for a single test case.

        Uses assertion-based grading instead of LLM grading.

        Args:
            test_case: The test case to evaluate
            output_dir: Not used for this evaluator (no files generated to disk)

        Returns:
            EvaluationResult with the evaluation outcome
        """
        self.logger.info(
            "Evaluating get_additional_models for test case: %s - %s",
            test_case.test_id,
            test_case.name,
        )

        # Load relevant models
        relevant_models = self.data_loader.load_models(test_case.model_files)
        if not relevant_models and test_case.model_files:
            return self._error_result(
                test_case,
                f"Failed to load model files: {', '.join(test_case.model_files)}",
            )

        # Load available models
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

            # Build evaluation results using assertions
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
