"""Models for evaluation datasets."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


EvaluationType = Literal["generate_first_test", "generate_models"]


class EvaluationTestCase(BaseModel):
    """Represents a single test case in the evaluation dataset."""

    model_config = ConfigDict(protected_namespaces=())

    case_type: EvaluationType = Field(
        default="generate_first_test",
        description="Type of evaluation to run (e.g., 'generate_first_test', 'generate_models')",
    )
    test_id: str = Field(description="Unique identifier for the test case (e.g., 'test_001')")
    name: str = Field(description="Name of the test case")
    api_definition_file: str = Field(
        description=(
            "Name of the API definition file (YAML) in the definitions folder. "
            "Should be prefixed with test_id (e.g., 'test_001_user_post_api.yaml')"
        )
    )
    model_files: List[str] = Field(
        default_factory=list,
        description=(
            "List of model file paths relative to the models folder. "
            "Filenames may start with a test prefix such as 'test_001_' "
            "which will be removed automatically (e.g., 'requests/test_001_UserModel.ts')."
        ),
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


class EvaluationSummary(BaseModel):
    """Aggregated summary when multiple datasets are evaluated."""

    total_datasets: int = Field(description="Number of datasets evaluated")
    total_test_cases: int = Field(description="Total test cases across all datasets")
    total_graded: int = Field(description="Total graded test cases across all datasets")
    total_not_evaluated: int = Field(description="Total not-evaluated test cases across all datasets")
    total_errors: int = Field(description="Total errors across all datasets")
    total_input_tokens: int = Field(description="Total input tokens across all datasets")
    total_output_tokens: int = Field(description="Total output tokens across all datasets")
    total_cost: float = Field(description="Total cost (USD) across all datasets")
    average_score_across_datasets: Optional[float] = Field(
        default=None,
        description="Average of dataset-level average scores, when available",
    )
    dataset_results: List[EvaluationRunResult] = Field(
        description="Individual dataset results included in the summary"
    )
