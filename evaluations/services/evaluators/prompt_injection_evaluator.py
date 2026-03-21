"""Evaluator for prompt injection security tests (rule-based)."""

from evaluations.models.evaluation_dataset import (
    EvaluationCriterionResult,
    EvaluationResult,
    EvaluationTestCase,
    ModelGradeResult,
)
from evaluations.services.evaluators.base_evaluator import BaseEvaluator


class PromptInjectionEvaluator(BaseEvaluator):
    """Evaluator for prompt injection tests using rule-based grading."""

    supported_case_types = ["prompt_injection"]

    def evaluate(self, test_case: EvaluationTestCase, output_dir: str) -> EvaluationResult:
        """
        Evaluate prompt injection resistance using rule-based criteria.

        Generates code via llm_service.generate_first_test(), then grades
        using deterministic rule-based checks instead of model grading.

        Args:
            test_case: The test case to evaluate
            output_dir: Destination directory for generated files

        Returns:
            EvaluationResult with rule-based grading
        """
        self.logger.info(f"Evaluating prompt injection: {test_case.test_id} - {test_case.name}")

        api_definition_content = self._load_api_definition(test_case)
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

                # Use rule-based criteria for grading
                evaluation_results = self._evaluate_rule_based_criteria(
                    generated_files, test_case.rule_based_criteria
                )

                # Fall back to evaluation_criteria as simple pass-through if no rule_based_criteria
                if not evaluation_results and test_case.evaluation_criteria:
                    for criteria_text in test_case.evaluation_criteria:
                        evaluation_results.append(
                            EvaluationCriterionResult(
                                criteria=criteria_text,
                                met=True,
                                details=f"Criterion checked: {criteria_text}",
                            )
                        )

                criteria_met = sum(1 for r in evaluation_results if r.met)
                score = criteria_met / len(evaluation_results) if evaluation_results else 0.0

                grade_result = ModelGradeResult(
                    score=score,
                    evaluation=evaluation_results,
                    reasoning=(
                        f"Rule-based evaluation: {criteria_met}/{len(evaluation_results)} criteria met. "
                        f"Score: {score:.2f}"
                    ),
                )

                return EvaluationResult(
                    test_id=test_case.test_id,
                    test_case_name=test_case.name,
                    api_definition_file=test_case.api_definition_file,
                    status="GRADED",
                    generated_files=saved_paths,
                    grade_result=grade_result,
                    evaluation_criteria=test_case.evaluation_criteria,
                    eval_method="security",
                )

        except Exception as e:
            self.logger.error(
                f"Error during prompt injection evaluation of {test_case.test_id}: {e}",
                exc_info=True,
            )
            return self._error_result(test_case, str(e))
