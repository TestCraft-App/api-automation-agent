"""Unit tests for FixTypescriptEvaluator."""

import os

import pytest
from unittest.mock import MagicMock

from evaluations.models.evaluation_dataset import (
    EvaluationCriterionResult,
    EvaluationTestCase,
    ModelGradeResult,
    RuleBasedCriterion,
)
from evaluations.services.evaluators.fix_typescript_evaluator import (
    FixTypescriptEvaluator,
)
from src.ai_tools.models.file_spec import FileSpec
from src.configuration.config import Config
from src.configuration.models import Model


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
    """Create a FixTypescriptEvaluator with mocked dependencies."""
    llm_service = MagicMock()
    data_loader = MagicMock()
    file_writer = MagicMock()
    model_grader = MagicMock()
    return FixTypescriptEvaluator(
        config=config,
        llm_service=llm_service,
        data_loader=data_loader,
        file_writer=file_writer,
        model_grader=model_grader,
    )


def _make_test_case(**overrides):
    """Helper to create an EvaluationTestCase for fix_typescript."""
    defaults = dict(
        case_type="fix_typescript",
        test_id="test_001",
        name="fix_test",
        broken_files=["test_001_broken.ts"],
        compiler_errors=["error TS2344: Type mismatch"],
        rule_based_criteria=[
            RuleBasedCriterion(
                check_type="not_contains",
                pattern="Response<",
                description="No Response wrapper",
            ),
        ],
        evaluation_criteria=["Fix preserves test logic"],
    )
    defaults.update(overrides)
    return EvaluationTestCase(**defaults)


def test_evaluate_fix_successful(evaluator, tmp_path):
    """When fix_typescript produces valid output, result is GRADED."""
    test_case = _make_test_case()

    evaluator.data_loader.load_first_test_file.return_value = FileSpec(
        path="src/tests/Create-User.spec.ts",
        fileContent=(
            "const response = await "
            "service.createUser<Response<UserModel>>(user);"
        ),
    )

    # Simulate fix_typescript writing fixed files to disk
    def mock_fix_typescript(files, messages):
        fixed_dir = os.path.join(str(tmp_path), "src", "tests")
        os.makedirs(fixed_dir, exist_ok=True)
        fixed_path = os.path.join(
            fixed_dir, "Create-User.spec.ts"
        )
        with open(fixed_path, "w", encoding="utf-8") as f:
            f.write(
                "const response = await "
                "service.createUser<UserModel>(user);"
            )

    evaluator.llm_service.fix_typescript.side_effect = (
        mock_fix_typescript
    )

    evaluator.model_grader.grade.return_value = ModelGradeResult(
        score=1.0,
        evaluation=[
            EvaluationCriterionResult(
                criteria="Fix preserves test logic",
                met=True,
                details="ok",
            )
        ],
        reasoning="Fix looks good",
    )

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "GRADED"
    assert result.grade_result is not None
    assert result.grade_result.score == 1.0
    assert result.eval_method == "hybrid"
    evaluator.llm_service.fix_typescript.assert_called_once()


def test_evaluate_returns_error_when_no_broken_files(
    evaluator, tmp_path
):
    """When broken_files is empty, result is ERROR."""
    test_case = _make_test_case(broken_files=[])

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "ERROR"
    assert "No broken_files specified" in result.error_message


def test_evaluate_returns_error_when_no_compiler_errors(
    evaluator, tmp_path
):
    """When compiler_errors is empty, result is ERROR."""
    test_case = _make_test_case(compiler_errors=[])

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.status == "ERROR"
    assert "No compiler_errors specified" in result.error_message


def test_evaluate_returns_hybrid_eval_method(evaluator, tmp_path):
    """The eval_method field should be 'hybrid'."""
    test_case = _make_test_case()

    evaluator.data_loader.load_first_test_file.return_value = FileSpec(
        path="src/tests/Create-User.spec.ts",
        fileContent=(
            "const response = await "
            "service.createUser<Response<UserModel>>(user);"
        ),
    )

    def mock_fix_typescript(files, messages):
        fixed_dir = os.path.join(str(tmp_path), "src", "tests")
        os.makedirs(fixed_dir, exist_ok=True)
        fixed_path = os.path.join(
            fixed_dir, "Create-User.spec.ts"
        )
        with open(fixed_path, "w", encoding="utf-8") as f:
            f.write(
                "const response = await "
                "service.createUser<UserModel>(user);"
            )

    evaluator.llm_service.fix_typescript.side_effect = (
        mock_fix_typescript
    )

    evaluator.model_grader.grade.return_value = ModelGradeResult(
        score=1.0,
        evaluation=[
            EvaluationCriterionResult(
                criteria="Fix preserves test logic",
                met=True,
                details="ok",
            )
        ],
        reasoning="Fix looks good",
    )

    result = evaluator.evaluate(test_case, str(tmp_path))

    assert result.eval_method == "hybrid"


def test_can_handle_fix_typescript(evaluator):
    """can_handle returns True for fix_typescript, False for others."""
    assert evaluator.can_handle("fix_typescript") is True
    assert evaluator.can_handle("prompt_injection") is False
    assert evaluator.can_handle("generate_first_test") is False
