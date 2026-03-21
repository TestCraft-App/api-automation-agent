"""Unit tests for PromptAdherenceEvaluator."""

import pytest
from unittest.mock import MagicMock

from evaluations.models.evaluation_dataset import (
    EvaluationCriterionResult,
    EvaluationTestCase,
    ModelGradeResult,
    RuleBasedCriterion,
)
from evaluations.services.evaluators.prompt_adherence_evaluator import (
    PromptAdherenceEvaluator,
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
        model=Model.CLAUDE_SONNET_4_5,
        destination_folder="test-folder",
        debug=False,
        langchain_debug=False,
    )


@pytest.fixture
def evaluator(config):
    """Create a PromptAdherenceEvaluator with mocked dependencies."""
    llm_service = MagicMock()
    data_loader = MagicMock()
    file_writer = MagicMock()
    model_grader = MagicMock()
    return PromptAdherenceEvaluator(
        config=config,
        llm_service=llm_service,
        data_loader=data_loader,
        file_writer=file_writer,
        model_grader=model_grader,
    )


def _make_test_case(**overrides):
    """Helper to create an EvaluationTestCase for prompt adherence."""
    defaults = dict(
        case_type="prompt_adherence",
        test_id="test_001",
        name="test_adherence",
        api_definition_file="test_api.yaml",
        model_files=["services/UserService.ts"],
        evaluation_criteria=[
            "Generated test follows prompt instructions",
        ],
        rule_based_criteria=[
            RuleBasedCriterion(
                check_type="contains",
                pattern="expect(",
                description="Uses expect assertions",
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


def test_evaluate_hybrid_all_pass(evaluator, tmp_path):
    """When both rule-based and model-graded criteria pass, score is 1.0."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent=(
                "describe('User', () => { "
                "it('works', () => { expect(true).to.be.true; }); });"
            ),
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


def test_evaluate_rule_criteria_fail(evaluator, tmp_path):
    """When rule criteria fail but model criteria pass, score is partial."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    # Code does not contain "expect(" -> rule-based criterion fails
    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent="describe('User', () => { it('works'); });",
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


def test_evaluate_returns_hybrid_eval_method(evaluator, tmp_path):
    """The eval_method field should be 'hybrid'."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent="expect(true);",
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


def test_can_handle_prompt_adherence(evaluator):
    """can_handle returns True for prompt_adherence, False for others."""
    assert evaluator.can_handle("prompt_adherence") is True
    assert evaluator.can_handle("prompt_injection") is False
    assert evaluator.can_handle("architectural_compliance") is False
