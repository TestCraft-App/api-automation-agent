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
            "Filenames may start with a test prefix such as 'test_001_' "
            "which will be removed automatically (e.g., 'requests/test_001_UserModel.ts')."
        )
    )
    evaluation_criteria: List[str] = Field(
        description="List of criteria used to evaluate if the generated test meets requirements"
    )


class EvaluationDataset(BaseModel):
    """Represents a complete evaluation dataset."""

    dataset_name: str = Field(description="Name of the evaluation dataset")
    test_cases: List[EvaluationTestCase] = Field(description="List of test cases in this dataset")


class EvaluationCriterionResult(BaseModel):
    """Represents the outcome for a single evaluation criterion."""

    criteria: str = Field(description="The evaluation criterion that was assessed")
    met: bool = Field(description="Whether the criterion was met")
    details: str = Field(description="Explanation describing why the criterion was or was not met")


class ModelGradeResult(BaseModel):
    """Result of model grading evaluation."""

    score: Optional[float] = Field(
        default=None, description="Score (0.0-1.0) reflecting how well the file met the criteria"
    )
    evaluation: List[EvaluationCriterionResult] = Field(
        default_factory=list,
        description="Detailed evaluation results for each criterion",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation summarizing how the score was determined",
    )


class EvaluationResult(BaseModel):
    """Result of a single evaluation test case."""

    test_id: str = Field(description="Unique identifier for the test case")
    test_case_name: str = Field(description="Name of the test case")
    api_definition_file: str = Field(description="API definition file used")
    status: str = Field(description="Status: GRADED, NOT_EVALUATED, ERROR")
    error_message: Optional[str] = Field(default=None, description="Error message if status is ERROR")
    generated_files: List[str] = Field(default_factory=list, description="Paths of generated test files")
    grade_result: Optional[ModelGradeResult] = Field(
        default=None, description="Model grading result if evaluation succeeded"
    )
    evaluation_criteria: List[str] = Field(
        description="Criteria that were evaluated against, in the original order"
    )


class EvaluationRunResult(BaseModel):
    """Complete result of an evaluation run."""

    dataset_name: str = Field(description="Name of the dataset evaluated")
    total_test_cases: int = Field(description="Total number of test cases")
    graded_count: int = Field(description="Number of test cases that produced a model-based grade")
    not_evaluated_count: int = Field(
        description="Number of test cases that did not produce files or could not be graded",
    )
    error_count: int = Field(description="Number of test cases that errored")
    total_input_tokens: int = Field(
        default=0, description="Total number of input tokens consumed across the evaluation"
    )
    total_output_tokens: int = Field(
        default=0, description="Total number of output tokens produced across the evaluation"
    )
    total_cost: float = Field(default=0.0, description="Total cost (in USD) incurred by the evaluation runs")
    average_score: Optional[float] = Field(
        default=None,
        description="Average score across all test cases that produced a score",
    )
    generated_files_path: Optional[str] = Field(
        default=None,
        description="Absolute path to the folder containing generated files for this run",
    )
    results: List[EvaluationResult] = Field(description="Detailed results for each test case")
