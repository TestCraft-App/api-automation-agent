"""Evaluator for prompt adherence (hybrid: rule-based + model-graded)."""

from typing import List

from evaluations.models.evaluation_dataset import (
    EvaluationCriterionResult,
    EvaluationResult,
    EvaluationTestCase,
    ModelGradeResult,
)
from evaluations.services.evaluators.base_evaluator import BaseEvaluator


class PromptAdherenceEvaluator(BaseEvaluator):
    """Evaluator for prompt adherence using hybrid grading (rule-based + model-graded).

    Combines deterministic structural checks with LLM-based semantic assessment
    into a composite score.
    """

    supported_case_types = ["prompt_adherence"]

    def evaluate(self, test_case: EvaluationTestCase, output_dir: str) -> EvaluationResult:
        """
        Evaluate prompt adherence using hybrid criteria.

        Generates code, then applies rule-based checks for structural adherence
        and model-graded checks for semantic quality, combining into a composite score.

        Args:
            test_case: The test case to evaluate
            output_dir: Destination directory for generated files

        Returns:
            EvaluationResult with hybrid grading
        """
        self.logger.info(f"Evaluating prompt adherence: {test_case.test_id} - {test_case.name}")

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

                all_criteria: List[EvaluationCriterionResult] = []

                # Rule-based structural checks
                if test_case.rule_based_criteria:
                    rule_results = self._evaluate_rule_based_criteria(
                        generated_files, test_case.rule_based_criteria
                    )
                    all_criteria.extend(rule_results)

                # Model-graded semantic checks
                if test_case.evaluation_criteria:
                    model_grade = self._evaluate_generated_files(
                        generated_files, test_case.evaluation_criteria
                    )
                    if model_grade and model_grade.evaluation:
                        all_criteria.extend(model_grade.evaluation)

                if not all_criteria:
                    return self._error_result(
                        test_case, "No criteria evaluated", status="NOT_EVALUATED"
                    )

                criteria_met = sum(1 for r in all_criteria if r.met)
                score = criteria_met / len(all_criteria)

                rule_count = len(test_case.rule_based_criteria)
                model_count = len(test_case.evaluation_criteria)

                grade_result = ModelGradeResult(
                    score=score,
                    evaluation=all_criteria,
                    reasoning=(
                        f"Hybrid prompt adherence: {criteria_met}/{len(all_criteria)} criteria met "
                        f"({rule_count} rule-based, {model_count} model-graded). "
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
                    eval_method="hybrid",
                )

        except Exception as e:
            self.logger.error(
                f"Error during prompt adherence evaluation of {test_case.test_id}: {e}",
                exc_info=True,
            )
            return self._error_result(test_case, str(e))
