"""Unit tests for rule-based criteria evaluation."""

import pytest
from unittest.mock import MagicMock

from src.ai_tools.models.file_spec import FileSpec
from src.configuration.config import Config
from src.configuration.models import Model
from evaluations.models.evaluation_dataset import RuleBasedCriterion
from evaluations.services.evaluators.base_evaluator import BaseEvaluator


class ConcreteEvaluator(BaseEvaluator):
    """Concrete evaluator for testing base class methods."""

    supported_case_types = ["test"]

    def evaluate(self, test_case, output_dir):
        pass


@pytest.fixture
def config():
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
    return ConcreteEvaluator(
        config=config,
        llm_service=MagicMock(),
        data_loader=MagicMock(),
        file_writer=MagicMock(),
        model_grader=MagicMock(),
    )


@pytest.fixture
def sample_files():
    return [
        FileSpec(
            path="src/tests/Create-User.spec.ts",
            fileContent=(
                'import { UserService } from "../models/services/UserService.js";\n'
                'import { UserModel } from "../models/requests/UserModel.js";\n\n'
                "describe('Create User', () => {\n"
                "  const userService = new UserService();\n\n"
                "  it('should create a user', async () => {\n"
                "    const user: UserModel = {\n"
                "      name: `Test User ${Date.now()}`,\n"
                "      email: `test${Date.now()}@example.com`,\n"
                "    };\n"
                "    const response = await userService.createUser<UserModel>(user);\n"
                "    response.status.should.equal(201);\n"
                "    response.data?.name.should.equal(user.name);\n"
                "  });\n"
                "});\n"
            ),
        )
    ]


def test_contains_check_passes(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(
            check_type="contains", pattern="describe(", description="Has describe block"
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is True


def test_contains_check_fails(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(check_type="contains", pattern="expect(", description="Has expect")
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is False


def test_not_contains_check_passes(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(check_type="not_contains", pattern="alert(", description="No alert")
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is True


def test_not_contains_check_fails(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(
            check_type="not_contains", pattern="describe(", description="No describe"
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is False


def test_regex_match_passes(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(
            check_type="regex_match", pattern=r"\.should\.equal\(", description="Has should.equal"
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is True


def test_regex_match_fails(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(
            check_type="regex_match", pattern=r"expect\(.*\)\.toBe", description="Has toBe"
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is False


def test_regex_not_match_passes(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(
            check_type="regex_not_match", pattern=r"\bvar\b", description="No var"
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is True


def test_regex_not_match_fails(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(
            check_type="regex_not_match", pattern=r"async\s+", description="No async"
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is False


def test_file_exists_check_passes(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(
            check_type="file_exists", pattern=".spec.ts", description="Has spec file"
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is True


def test_file_exists_check_fails(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(
            check_type="file_exists", pattern="Response.ts", description="Has Response"
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is False


def test_import_check_passes(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(
            check_type="import_check", pattern="UserService", description="Imports UserService"
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is True


def test_import_check_fails(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(
            check_type="import_check", pattern="ProductService",
            description="Imports ProductService",
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 1
    assert results[0].met is False


def test_multiple_criteria(evaluator, sample_files):
    criteria = [
        RuleBasedCriterion(check_type="contains", pattern="describe(", description="Has describe"),
        RuleBasedCriterion(check_type="not_contains", pattern="alert(", description="No alert"),
        RuleBasedCriterion(check_type="regex_match", pattern=r"\.js['\"]", description="JS extension"),
        RuleBasedCriterion(check_type="not_contains", pattern="expect(", description="No expect"),
    ]
    results = evaluator._evaluate_rule_based_criteria(sample_files, criteria)
    assert len(results) == 4
    assert all(r.met for r in results)


def test_target_file_filter(evaluator):
    files = [
        FileSpec(path="src/tests/Create-User.spec.ts", fileContent="describe('test', () => {});"),
        FileSpec(path="src/models/UserModel.ts", fileContent="export interface UserModel { name: string; }"),
    ]
    criteria = [
        RuleBasedCriterion(
            check_type="contains",
            pattern="describe(",
            description="Test file has describe",
            target_file="Create-User.spec.ts",
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(files, criteria)
    assert len(results) == 1
    assert results[0].met is True


def test_target_file_filter_no_match(evaluator):
    files = [
        FileSpec(path="src/tests/Create-User.spec.ts", fileContent="describe('test', () => {});"),
        FileSpec(path="src/models/UserModel.ts", fileContent="export interface UserModel { name: string; }"),
    ]
    criteria = [
        RuleBasedCriterion(
            check_type="contains",
            pattern="describe(",
            description="Model file has describe",
            target_file="UserModel.ts",
        )
    ]
    results = evaluator._evaluate_rule_based_criteria(files, criteria)
    assert len(results) == 1
    assert results[0].met is False


def test_empty_criteria_returns_empty(evaluator, sample_files):
    results = evaluator._evaluate_rule_based_criteria(sample_files, [])
    assert len(results) == 0
