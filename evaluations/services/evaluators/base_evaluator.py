"""Abstract base class for evaluation strategies."""

import json
import os
import shutil
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Generator, List, Literal, Optional, Sequence

from src.ai_tools.models.file_spec import FileSpec
from src.configuration.config import Config
from src.configuration.data_sources import DataSource
from src.processors.postman.postman_utils import PostmanUtils
from src.services.llm_service import LLMService
from src.utils.logger import Logger
from evaluations.models.evaluation_dataset import (
    EvaluationCriterionResult,
    EvaluationResult,
    EvaluationTestCase,
    ModelGradeResult,
)
from evaluations.services.evaluation_data_loader import EvaluationDataLoader
from evaluations.services.evaluation_file_writer import EvaluationFileWriter
from evaluations.services.model_grader import ModelGrader


class BaseEvaluator(ABC):
    """Abstract base class for all evaluators."""

    # Subclasses should define which case_types they handle
    supported_case_types: List[str] = []

    def __init__(
        self,
        config: Config,
        llm_service: LLMService,
        data_loader: EvaluationDataLoader,
        file_writer: EvaluationFileWriter,
        model_grader: ModelGrader,
    ):
        """
        Initialize the evaluator with shared dependencies.

        Args:
            config: Configuration object
            llm_service: LLMService instance for generating tests
            data_loader: EvaluationDataLoader for loading test data
            file_writer: EvaluationFileWriter for saving generated files
            model_grader: ModelGrader for grading generated files
        """
        self.config = config
        self.llm_service = llm_service
        self.data_loader = data_loader
        self.file_writer = file_writer
        self.model_grader = model_grader
        self.logger = Logger.get_logger(self.__class__.__name__)

    def can_handle(self, case_type: str) -> bool:
        """Check if this evaluator can handle the given case type."""
        return case_type in self.supported_case_types

    @abstractmethod
    def evaluate(self, test_case: EvaluationTestCase, output_dir: str) -> EvaluationResult:
        """
        Evaluate a test case.

        Args:
            test_case: The test case to evaluate
            output_dir: Directory for output files

        Returns:
            EvaluationResult with the evaluation outcome
        """
        pass

    # -------------------------------------------------------------------------
    # Shared Helper Methods
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
        """Evaluate generated files against criteria using model grading."""
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
                reasoning="The generation method returned an empty list",
            )

        combined_content = "\n\n".join(
            f"// File: {file.path}\n{file.fileContent}" for file in generated_files
        )

        return self.model_grader.grade(combined_content, evaluation_criteria)

    def _is_postman_case(self, case_type: str) -> bool:
        """Check if the case type is a Postman variant."""
        return "postman" in case_type.lower()

    def _preprocess_postman_definition(self, raw_content: str) -> Optional[str]:
        """
        Preprocess a raw Postman collection into the format expected by llm_service.

        Args:
            raw_content: Raw Postman collection JSON string

        Returns:
            Preprocessed JSON string, or None if parsing fails
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

    def _load_api_definition(self, test_case: EvaluationTestCase) -> Optional[str]:
        """
        Load and optionally preprocess API definition based on case type.

        For Postman case types, the definition is preprocessed.
        For other case types, the raw definition is returned.

        Args:
            test_case: The test case containing api_definition_file and case_type

        Returns:
            API definition content (preprocessed for Postman), or None if loading fails
        """
        raw_definition = self.data_loader.load_api_definition(test_case.api_definition_file)
        if not raw_definition:
            return None

        if self._is_postman_case(test_case.case_type):
            return self._preprocess_postman_definition(raw_definition)

        return raw_definition

    def _get_data_source_for_case(self, case_type: str) -> Optional[DataSource]:
        """Get the appropriate DataSource for a case type, or None for default."""
        if self._is_postman_case(case_type):
            return DataSource.POSTMAN
        return None
