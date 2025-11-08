"""Service for running evaluations on LLMService generation methods."""

import os
import re
import shutil
from datetime import datetime
from typing import List, Optional, Sequence

from src.ai_tools.models.file_spec import FileSpec
from src.configuration.config import Config
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


class EvaluationRunner:
    """Service for running evaluations on LLMService methods."""

    def __init__(
        self,
        config: Config,
        llm_service: LLMService,
        file_service: FileService,
        test_data_folder: str,
        model_grader: Optional[ModelGrader] = None,
    ):
        """
        Initialize the Evaluation Runner.

        Args:
            config: Configuration object
            llm_service: LLMService instance for generating tests
            file_service: FileService instance for file operations
            test_data_folder: Path to folder containing test data (API definition files)
            model_grader: Optional ModelGrader instance. If not provided, will create one.
        """
        self.config = config
        self.llm_service = llm_service
        self.file_service = file_service
        self.test_data_folder = test_data_folder
        self.logger = Logger.get_logger(__name__)
        self.model_grader = model_grader or ModelGrader(config)

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

    def _normalize_model_path(self, path: str) -> str:
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
        generated_models = []
        for model_file in model_files:
            file_path = os.path.join(models_folder, model_file)
            if not os.path.exists(file_path):
                self.logger.warning(f"Model file not found: {file_path}, skipping")
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                clean_path = self._normalize_model_path(model_file)
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

            grade_result = self._evaluate_generated_files(generated_files, test_case.evaluation_criteria)

            status = "GRADED" if grade_result else "NOT_EVALUATED"

            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status=status,
                generated_files=[f.path for f in generated_files],
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

            grade_result = self._evaluate_generated_files(file_specs, test_case.evaluation_criteria)
            status = "GRADED" if grade_result else "NOT_EVALUATED"

            return EvaluationResult(
                test_id=test_case.test_id,
                test_case_name=test_case.name,
                api_definition_file=test_case.api_definition_file,
                status=status,
                generated_files=[spec.path for spec in file_specs],
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

    def run_evaluation(self, dataset: EvaluationDataset) -> EvaluationRunResult:
        """
        Run evaluation on all test cases in a dataset.

        Args:
            dataset: The evaluation dataset to run

        Returns:
            EvaluationRunResult with aggregated results
        """
        self.logger.info(f"\nStarting evaluation run for dataset: {dataset.dataset_name}")
        print(f"Using LLM model: {self.config.model.name} ({self.config.model.value})")
        self.logger.info(f"Number of test cases: {len(dataset.test_cases)}\n")

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

        for test_case in dataset.test_cases:
            test_output_dir = os.path.join(base_output_dir, test_case.test_id)

            if test_case.case_type == "generate_models":
                result = self.evaluate_generate_models(test_case, test_output_dir)
            elif test_case.case_type == "generate_first_test":
                result = self.evaluate_generate_first_test(test_case, test_output_dir)
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

            results.append(result)

            if result.status == "GRADED":
                graded_count += 1
            elif result.status == "NOT_EVALUATED":
                not_evaluated_count += 1
            else:
                error_count += 1

            if result.grade_result and result.grade_result.score is not None:
                scores.append(result.grade_result.score)

            self.logger.info(f"Test case '{test_case.name}': {result.status}\n")

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
            total_test_cases=len(dataset.test_cases),
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
