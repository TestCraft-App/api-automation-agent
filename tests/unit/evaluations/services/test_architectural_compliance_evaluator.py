"""Unit tests for ArchitecturalComplianceEvaluator."""

import pytest
from unittest.mock import MagicMock

from evaluations.models.evaluation_dataset import (
    EvaluationTestCase,
    RuleBasedCriterion,
)
from evaluations.services.evaluators.architectural_compliance_evaluator import (
    ArchitecturalComplianceEvaluator,
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
    """Create an ArchitecturalComplianceEvaluator with mocked dependencies."""
    llm_service = MagicMock()
    data_loader = MagicMock()
    file_writer = MagicMock()
    model_grader = MagicMock()
    return ArchitecturalComplianceEvaluator(
        config=config,
        llm_service=llm_service,
        data_loader=data_loader,
        file_writer=file_writer,
        model_grader=model_grader,
    )


def _make_test_case(**overrides):
    """Helper to create an EvaluationTestCase with sensible defaults."""
    defaults = dict(
        case_type="architectural_compliance",
        test_id="test_001",
        name="test_architecture",
        api_definition_file="test_api.yaml",
        model_files=["services/UserService.ts"],
        evaluation_criteria=[],
        rule_based_criteria=[
            RuleBasedCriterion(
                check_type="contains",
                pattern="import",
                description="Has import statements",
            ),
            RuleBasedCriterion(
                check_type="contains",
                pattern="describe(",
                description="Uses describe blocks",
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


def test_evaluate_all_rules_pass(evaluator, tmp_path):
    """When all rule-based checks pass, score is 1.0."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent=(
                "import { UserService } from '../services';\n"
                "describe('User', () => { it('works'); });"
            ),
        )
    ]
    evaluator.file_writer.save_generated_files.return_value = [
        "src/tests/Create-User.spec.ts"
    ]

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "GRADED"
    assert result.grade_result is not None
    assert result.grade_result.score == 1.0
    assert result.eval_method == "rule_based"


def test_evaluate_some_rules_fail(evaluator, tmp_path):
    """When some checks fail, score reflects the ratio of passed criteria."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    # Code has "import" but not "describe(" -> 1 out of 2 criteria met
    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent=(
                "import { UserService } from '../services';\n"
                "it('works');"
            ),
        )
    ]
    evaluator.file_writer.save_generated_files.return_value = [
        "src/tests/Create-User.spec.ts"
    ]

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "GRADED"
    assert result.grade_result is not None
    assert result.grade_result.score == 0.5


def test_evaluate_returns_rule_based_eval_method(evaluator, tmp_path):
    """The eval_method field should be 'rule_based'."""
    test_case = _make_test_case()
    _mock_standard_setup(evaluator)

    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent="import x;\ndescribe('test', () => {});",
        )
    ]
    evaluator.file_writer.save_generated_files.return_value = [
        "src/tests/Create-User.spec.ts"
    ]

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.eval_method == "rule_based"


def test_evaluate_returns_not_evaluated_when_no_rule_criteria(
    evaluator, tmp_path
):
    """When no rule_based_criteria are defined, result is NOT_EVALUATED."""
    test_case = _make_test_case(rule_based_criteria=[])
    _mock_standard_setup(evaluator)

    evaluator.llm_service.generate_first_test.return_value = [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent="some code",
        )
    ]
    evaluator.file_writer.save_generated_files.return_value = [
        "src/tests/Create-User.spec.ts"
    ]

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "NOT_EVALUATED"
    assert "No rule-based criteria defined" in result.error_message


def test_can_handle_architectural_compliance(evaluator):
    """can_handle returns True for architectural_compliance, False for others."""
    assert evaluator.can_handle("architectural_compliance") is True
    assert evaluator.can_handle("prompt_injection") is False
    assert evaluator.can_handle("hallucination_detection") is False
