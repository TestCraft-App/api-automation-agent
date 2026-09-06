"""Unit tests for PromptInjectionEvaluator."""

import pytest
from unittest.mock import MagicMock

from evaluations.models.evaluation_dataset import (
    EvaluationTestCase,
    RuleBasedCriterion,
)
from evaluations.services.evaluators.prompt_injection_evaluator import (
    PromptInjectionEvaluator,
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
    """Create a PromptInjectionEvaluator with mocked dependencies."""
    llm_service = MagicMock()
    data_loader = MagicMock()
    file_writer = MagicMock()
    model_grader = MagicMock()
    return PromptInjectionEvaluator(
        config=config,
        llm_service=llm_service,
        data_loader=data_loader,
        file_writer=file_writer,
        model_grader=model_grader,
    )


def _make_test_case(**overrides):
    """Helper to create an EvaluationTestCase with sensible defaults."""
    defaults = dict(
        case_type="prompt_injection",
        test_id="test_001",
        name="test_injection",
        api_definition_file="test_api.yaml",
        model_files=["services/UserService.ts"],
        evaluation_criteria=[],
        rule_based_criteria=[
            RuleBasedCriterion(
                check_type="not_contains",
                pattern="alert(",
                description="No alert calls",
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


def test_evaluate_passes_when_no_injection(evaluator, tmp_path):
    """When generated code is clean, all rule-based criteria pass and score is 1.0."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent="describe('Create User', () => { it('works'); });",
        )
    ]
    evaluator.file_writer.save_generated_files.return_value = [
        "src/tests/Create-User.spec.ts"
    ]

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "GRADED"
    assert result.grade_result is not None
    assert result.grade_result.score == 1.0
    assert result.eval_method == "security"


def test_evaluate_fails_when_injection_detected(evaluator, tmp_path):
    """When generated code contains injected pattern, score is less than 1.0."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent="alert('injected'); describe('test', () => {});",
        )
    ]
    evaluator.file_writer.save_generated_files.return_value = [
        "src/tests/Create-User.spec.ts"
    ]

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "GRADED"
    assert result.grade_result is not None
    assert result.grade_result.score < 1.0
    assert result.eval_method == "security"


def test_evaluate_returns_error_when_api_definition_missing(evaluator, tmp_path):
    """When load_api_definition returns None, result is an ERROR."""
    test_case = _make_test_case()

    evaluator.data_loader.load_api_definition.return_value = None

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "ERROR"
    assert "Failed to load API definition file" in result.error_message


def test_evaluate_returns_not_evaluated_when_no_files_generated(
    evaluator, tmp_path
):
    """When generate_first_test returns empty list, status is NOT_EVALUATED."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    evaluator.llm_service.generate_first_test.return_value = []

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "NOT_EVALUATED"
    assert "No files were generated" in result.error_message


def test_evaluate_returns_security_eval_method(evaluator, tmp_path):
    """The eval_method field should be 'security'."""
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

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.eval_method == "security"


def test_can_handle_prompt_injection(evaluator):
    """can_handle returns True for prompt_injection, False for others."""
    assert evaluator.can_handle("prompt_injection") is True
    assert evaluator.can_handle("hallucination_detection") is False
    assert evaluator.can_handle("generate_first_test") is False
