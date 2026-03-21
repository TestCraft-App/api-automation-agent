"""Evaluator for fix_typescript pipeline step (hybrid: rule-based + model-graded)."""

from typing import List

from src.ai_tools.models.file_spec import FileSpec
from evaluations.models.evaluation_dataset import (
    EvaluationCriterionResult,
    EvaluationResult,
    EvaluationTestCase,
    ModelGradeResult,
)
from evaluations.services.evaluators.base_evaluator import BaseEvaluator


class FixTypescriptEvaluator(BaseEvaluator):
    """Evaluator for fix_typescript method using hybrid grading.

    Tests the LLM's ability to fix intentional TypeScript errors.
    Rule-based checks verify error patterns are removed;
    model-graded checks verify fix preserves logic.
    """

    supported_case_types = ["fix_typescript"]

    def evaluate(self, test_case: EvaluationTestCase, output_dir: str) -> EvaluationResult:
        """
        Evaluate the fix_typescript method for a single test case.

        Loads broken files and compiler errors, calls fix_typescript,
        then grades using hybrid criteria (rule-based + model-graded).

        Args:
            test_case: The test case with broken_files and compiler_errors
            output_dir: Destination directory for generated files

        Returns:
            EvaluationResult with hybrid grading
        """
        self.logger.info(f"Evaluating fix_typescript: {test_case.test_id} - {test_case.name}")

        if not test_case.broken_files:
            return self._error_result(test_case, "No broken_files specified in test case")

        if not test_case.compiler_errors:
            return self._error_result(test_case, "No compiler_errors specified in test case")

        # Load broken files
        broken_file_specs: List[FileSpec] = []
        for broken_file in test_case.broken_files:
            file_spec = self.data_loader.load_first_test_file(broken_file)
            if file_spec:
                broken_file_specs.append(file_spec)

        if not broken_file_specs:
            return self._error_result(
                test_case, f"Failed to load broken files: {', '.join(test_case.broken_files)}"
            )

        self._setup_output_dir(output_dir)

        try:
            with self._temporary_config(destination_folder=output_dir):
                # Call fix_typescript - it modifies files in place via tool calls
                self.llm_service.fix_typescript(
                    files=broken_file_specs,
                    messages=test_case.compiler_errors,
                )

                # After fix_typescript, read the fixed files from the output directory
                import os

                fixed_files: List[FileSpec] = []
                for root, _, filenames in os.walk(output_dir):
                    for filename in filenames:
                        if filename.endswith(".ts"):
                            file_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(file_path, output_dir)
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            fixed_files.append(FileSpec(path=rel_path, fileContent=content))

                if not fixed_files:
                    # Fall back to original files if fix_typescript didn't write to disk
                    fixed_files = broken_file_specs

                saved_paths = [f.path for f in fixed_files]

                all_criteria: List[EvaluationCriterionResult] = []

                # Rule-based: check that error patterns are gone
                if test_case.rule_based_criteria:
                    rule_results = self._evaluate_rule_based_criteria(
                        fixed_files, test_case.rule_based_criteria
                    )
                    all_criteria.extend(rule_results)

                # Model-graded: check that fix preserves logic
                if test_case.evaluation_criteria:
                    model_grade = self._evaluate_generated_files(
                        fixed_files, test_case.evaluation_criteria
                    )
                    if model_grade and model_grade.evaluation:
                        all_criteria.extend(model_grade.evaluation)

                if not all_criteria:
                    return self._error_result(
                        test_case, "No criteria evaluated", status="NOT_EVALUATED"
                    )

                criteria_met = sum(1 for r in all_criteria if r.met)
                score = criteria_met / len(all_criteria)

                grade_result = ModelGradeResult(
                    score=score,
                    evaluation=all_criteria,
                    reasoning=(
                        f"Fix TypeScript hybrid: {criteria_met}/{len(all_criteria)} criteria met. "
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
                f"Error during fix_typescript evaluation of {test_case.test_id}: {e}",
                exc_info=True,
            )
            return self._error_result(test_case, str(e))
