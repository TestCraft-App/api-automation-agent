"""Models for evaluation datasets."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class EvaluationTestCase(BaseModel):
    """Represents a single test case in the evaluation dataset."""

    model_config = ConfigDict(protected_namespaces=())

    test_id: str = Field(description="Unique identifier for the test case (e.g., 'test_001')")
    name: str = Field(description="Name of the test case")
    api_definition_file: str = Field(
        description=(
            "Name of the API definition file (YAML) in the definitions folder. "
            "Should be prefixed with test_id (e.g., 'test_001_user_post_api.yaml')"
        )
    )
    model_files: List[str] = Field(
        description=(
            "List of model file paths relative to the models folder. "
            "The filename should be prefixed with test_id "
            "(e.g., 'requests/test_001_UserModel.ts'). "
        )
    )
    evaluation_criteria: str = Field(
        description="Criteria used to evaluate if the generated test meets requirements"
    )


class EvaluationDataset(BaseModel):
    """Represents a complete evaluation dataset."""

    dataset_name: str = Field(description="Name of the evaluation dataset")
    test_cases: List[EvaluationTestCase] = Field(description="List of test cases in this dataset")


class ModelGradeResult(BaseModel):
    """Result of model grading evaluation."""

    passed: bool = Field(description="Whether the generated file meets the criteria")
    score: Optional[float] = Field(default=None, description="Optional score (0.0-1.0) for the evaluation")
    feedback: str = Field(description="Detailed feedback from the model grader about why it passed or failed")
    reasoning: Optional[str] = Field(default=None, description="Optional reasoning from the model grader")


class EvaluationResult(BaseModel):
    """Result of a single evaluation test case."""

    test_id: str = Field(description="Unique identifier for the test case")
    test_case_name: str = Field(description="Name of the test case")
    api_definition_file: str = Field(description="API definition file used")
    status: str = Field(description="Status: SUCCESS, FAILED, ERROR")
    error_message: Optional[str] = Field(default=None, description="Error message if status is ERROR")
    generated_files: List[str] = Field(default_factory=list, description="Paths of generated test files")
    grade_result: Optional[ModelGradeResult] = Field(
        default=None, description="Model grading result if evaluation succeeded"
    )
    evaluation_criteria: str = Field(description="Criteria that was evaluated against")


class EvaluationRunResult(BaseModel):
    """Complete result of an evaluation run."""

    dataset_name: str = Field(description="Name of the dataset evaluated")
    total_test_cases: int = Field(description="Total number of test cases")
    passed_count: int = Field(description="Number of test cases that passed")
    failed_count: int = Field(description="Number of test cases that failed")
    error_count: int = Field(description="Number of test cases that errored")
    results: List[EvaluationResult] = Field(description="Detailed results for each test case")
