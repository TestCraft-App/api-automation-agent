"""Evaluator for generate_additional_tests."""

from evaluations.models.evaluation_dataset import EvaluationResult, EvaluationTestCase
from evaluations.services.evaluators.base_evaluator import BaseEvaluator


class AdditionalTestsEvaluator(BaseEvaluator):
    """Evaluator for generate_additional_tests method."""

    supported_case_types = ["generate_additional_tests"]

    def evaluate(self, test_case: EvaluationTestCase, output_dir: str) -> EvaluationResult:
        """
        Evaluate the generate_additional_tests method for a single test case.

        Args:
            test_case: The test case to evaluate
            output_dir: Destination directory where generated files should be written

        Returns:
            EvaluationResult with the evaluation outcome
        """
        self.logger.info(
            "Evaluating additional tests for test case: %s - %s",
            test_case.test_id,
            test_case.name,
        )

        api_definition_content = self._load_api_definition(test_case)
        if not api_definition_content:
            return self._error_result(
                test_case,
                f"Failed to load API definition file: {test_case.api_definition_file}",
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
                        test_case,
                        "No additional tests were generated",
                        status="NOT_EVALUATED",
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
