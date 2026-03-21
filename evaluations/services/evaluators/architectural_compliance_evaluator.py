"""Evaluator for architectural compliance (purely rule-based)."""

from evaluations.models.evaluation_dataset import (
    EvaluationResult,
    EvaluationTestCase,
    ModelGradeResult,
)
from evaluations.services.evaluators.base_evaluator import BaseEvaluator


class ArchitecturalComplianceEvaluator(BaseEvaluator):
    """Evaluator for architectural compliance using purely rule-based grading.

    All checks are deterministic regex/string pattern checks -- zero LLM grading cost.
    """

    supported_case_types = ["architectural_compliance"]

    def evaluate(self, test_case: EvaluationTestCase, output_dir: str) -> EvaluationResult:
        """
        Evaluate architectural compliance using rule-based criteria only.

        Generates code via llm_service.generate_first_test(), then grades
        using deterministic rule-based checks.

        Args:
            test_case: The test case to evaluate
            output_dir: Destination directory for generated files

        Returns:
            EvaluationResult with rule-based grading
        """
        self.logger.info(f"Evaluating architectural compliance: {test_case.test_id} - {test_case.name}")

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

                evaluation_results = self._evaluate_rule_based_criteria(
                    generated_files, test_case.rule_based_criteria
                )

                if not evaluation_results:
                    return self._error_result(
                        test_case, "No rule-based criteria defined", status="NOT_EVALUATED"
                    )

                criteria_met = sum(1 for r in evaluation_results if r.met)
                score = criteria_met / len(evaluation_results)

                grade_result = ModelGradeResult(
                    score=score,
                    evaluation=evaluation_results,
                    reasoning=(
                        f"Rule-based architectural compliance: {criteria_met}/{len(evaluation_results)} "
                        f"checks passed. Score: {score:.2f}"
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
                    eval_method="rule_based",
                )

        except Exception as e:
            self.logger.error(
                f"Error during architectural compliance evaluation of {test_case.test_id}: {e}",
                exc_info=True,
            )
            return self._error_result(test_case, str(e))
