"""Evaluator for generate_models (OpenAPI and Postman)."""

from src.ai_tools.models.file_spec import FileSpec
from evaluations.models.evaluation_dataset import EvaluationResult, EvaluationTestCase
from evaluations.services.evaluators.base_evaluator import BaseEvaluator


class ModelsEvaluator(BaseEvaluator):
    """Evaluator for generate_models method (handles both OpenAPI and Postman)."""

    supported_case_types = ["generate_models", "generate_models_postman"]

    def evaluate(self, test_case: EvaluationTestCase, output_dir: str) -> EvaluationResult:
        """
        Evaluate the generate_models method for a single test case.

        Handles both OpenAPI and Postman case types. For Postman, the API definition
        is automatically preprocessed to match the expected format.

        Args:
            test_case: The test case to evaluate
            output_dir: Destination directory where generated files should be written

        Returns:
            EvaluationResult with the evaluation outcome
        """
        self.logger.info(f"Evaluating models for test case: {test_case.test_id} - {test_case.name}")

        api_definition_content = self._load_api_definition(test_case)
        if not api_definition_content:
            error_msg = (
                "Failed to preprocess Postman collection"
                if self._is_postman_case(test_case.case_type)
                else f"Failed to load API definition file: {test_case.api_definition_file}"
            )
            return self._error_result(test_case, error_msg)

        self._setup_output_dir(output_dir)

        config_overrides = {"destination_folder": output_dir}
        data_source = self._get_data_source_for_case(test_case.case_type)
        if data_source:
            config_overrides["data_source"] = data_source

        try:
            with self._temporary_config(**config_overrides):
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
                f"Error during model evaluation of test case " f"{test_case.test_id} - {test_case.name}: {e}",
                exc_info=True,
            )
            return self._error_result(test_case, str(e))
