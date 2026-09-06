"""Unit tests for HallucinationEvaluator."""

import pytest
from unittest.mock import MagicMock

from evaluations.models.evaluation_dataset import (
    EvaluationCriterionResult,
    EvaluationTestCase,
    ModelGradeResult,
    RuleBasedCriterion,
)
from evaluations.services.evaluators.hallucination_evaluator import (
    HallucinationEvaluator,
)
from src.ai_tools.models.file_spec import FileSpec
from src.configuration.config import Config
from src.configuration.models import Model
from src.models.generated_model import GeneratedModel


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(
        openai_api_key="test",
        anthropic_api_key="test",
        google_api_key="test",
        model=Model.CLAUDE_SONNET_5,
        destination_folder="test-folder",
        debug=False,
        langchain_debug=False,
    )


@pytest.fixture
def evaluator(config):
    """Create a HallucinationEvaluator with mocked dependencies."""
    llm_service = MagicMock()
    data_loader = MagicMock()
    file_writer = MagicMock()
    model_grader = MagicMock()
    return HallucinationEvaluator(
        config=config,
        llm_service=llm_service,
        data_loader=data_loader,
        file_writer=file_writer,
        model_grader=model_grader,
    )


def _make_test_case(**overrides):
    """Helper to create an EvaluationTestCase for hallucination tests."""
    defaults = dict(
        case_type="hallucination_detection",
        test_id="test_001",
        name="test_hallucination",
        api_definition_file="test_api.yaml",
        model_files=["services/UserService.ts"],
        evaluation_criteria=[
            "Generated code should not invent API fields",
        ],
        rule_based_criteria=[
            RuleBasedCriterion(
                check_type="not_contains",
                pattern="fakeField",
                description="No hallucinated fakeField",
            ),
        ],
    )
    defaults.update(overrides)
    return EvaluationTestCase(**defaults)


def _mock_standard_setup(evaluator):
    """Set up common mock return values for data_loader."""
    evaluator.data_loader.load_api_definition.return_value = (
        "openapi: 3.0.0\ninfo:\n  title: Test API"
    )
    evaluator.data_loader.load_models.return_value = [
        GeneratedModel(
            path="src/models/services/UserService.ts",
            fileContent="export class UserService {}",
            summary="",
        )
    ]


def test_evaluate_passes_hybrid_criteria(evaluator, tmp_path):
    """When both rule-based and model-graded criteria pass, score is 1.0."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent="describe('User', () => { it('creates'); });",
        )
    ]
    evaluator.file_writer.save_generated_files.return_value = [
        "src/tests/Create-User.spec.ts"
    ]
    evaluator.model_grader.grade.return_value = ModelGradeResult(
        score=1.0,
        evaluation=[
            EvaluationCriterionResult(
                criteria="test", met=True, details="ok"
            )
        ],
        reasoning="All good",
    )

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "GRADED"
    assert result.grade_result is not None
    assert result.grade_result.score == 1.0
    assert result.eval_method == "hybrid"


def test_evaluate_fails_rule_based_criteria(evaluator, tmp_path):
    """When generated code contains a hallucinated field, rule-based check fails."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent="const x = response.fakeField;",
        )
    ]
    evaluator.file_writer.save_generated_files.return_value = [
        "src/tests/Create-User.spec.ts"
    ]
    evaluator.model_grader.grade.return_value = ModelGradeResult(
        score=1.0,
        evaluation=[
            EvaluationCriterionResult(
                criteria="test", met=True, details="ok"
            )
        ],
        reasoning="Model criteria passed",
    )

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "GRADED"
    assert result.grade_result is not None
    # 1 rule fails + 1 model passes = 1/2 = 0.5
    assert result.grade_result.score == 0.5


def test_evaluate_returns_error_when_no_models(evaluator, tmp_path):
    """When load_models returns empty list, result is ERROR."""
    test_case = _make_test_case()

    evaluator.data_loader.load_api_definition.return_value = (
        "openapi: 3.0.0\ninfo:\n  title: Test API"
    )
    evaluator.data_loader.load_models.return_value = []

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "ERROR"
    assert "Failed to load model files" in result.error_message


def test_evaluate_returns_hybrid_eval_method(evaluator, tmp_path):
    """The eval_method field should be 'hybrid'."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent="clean code",
        )
    ]
    evaluator.file_writer.save_generated_files.return_value = [
        "src/tests/Create-User.spec.ts"
    ]
    evaluator.model_grader.grade.return_value = ModelGradeResult(
        score=1.0,
        evaluation=[
            EvaluationCriterionResult(
                criteria="test", met=True, details="ok"
            )
        ],
        reasoning="All good",
    )

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.eval_method == "hybrid"


def test_can_handle_hallucination_detection(evaluator):
    """can_handle returns True for hallucination_detection, False for others."""
    assert evaluator.can_handle("hallucination_detection") is True
    assert evaluator.can_handle("prompt_injection") is False
    assert evaluator.can_handle("generate_first_test") is False
