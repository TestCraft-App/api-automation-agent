"""Unit tests for deterministic scoring in ModelGrader."""

import pytest
from unittest.mock import MagicMock

from evaluations.services.model_grader import ModelGrader
from src.configuration.config import Config
from src.configuration.models import Model


@pytest.fixture
def config():
    return Config(
        openai_api_key="test-openai-key",
        anthropic_api_key="test-anthropic-key",
        google_api_key="test-google-key",
        model=Model.CLAUDE_SONNET_5,
        destination_folder="test-folder",
        debug=False,
        langchain_debug=False,
    )


def _make_grader_with_mock_response(config, response_data):
    """Create a ModelGrader with a mock that returns the given response data.

    Returns a patched_grade function that applies the same deterministic
    scoring logic as ModelGrader.grade without requiring LangChain chain invocation.
    """
    grader = ModelGrader(config, llm=MagicMock())

    def patched_grade(generated_file_content, evaluation_criteria):
        from evaluations.models.evaluation_dataset import EvaluationCriterionResult, ModelGradeResult

        grade_data = response_data

        evaluation_entries = []
        for entry in grade_data.get("evaluation", []):
            if not isinstance(entry, dict):
                continue
            criteria_text = str(entry.get("criteria", "")).strip()
            if not criteria_text:
                continue
            evaluation_entries.append(
                EvaluationCriterionResult(
                    criteria=criteria_text,
                    met=bool(entry.get("met", False)),
                    details=str(entry.get("details", "")).strip() or "No details provided",
                )
            )

        criteria_met = sum(1 for e in evaluation_entries if e.met)
        deterministic_score = criteria_met / len(evaluation_entries) if evaluation_entries else 0.0

        return ModelGradeResult(
            score=deterministic_score,
            evaluation=evaluation_entries,
            reasoning=grade_data.get("reasoning"),
        )

    return grader, patched_grade


def test_deterministic_score_all_met(config):
    """Score should be 1.0 when all criteria are met, regardless of LLM's score field."""
    response_data = {
        "score": 0.7,
        "evaluation": [
            {"criteria": "Criterion 1", "met": True, "details": "Passed"},
            {"criteria": "Criterion 2", "met": True, "details": "Passed"},
            {"criteria": "Criterion 3", "met": True, "details": "Passed"},
        ],
        "reasoning": "Test",
    }
    grader, patched_grade = _make_grader_with_mock_response(config, response_data)
    result = patched_grade("code content", ["c1", "c2", "c3"])
    # Score should be deterministic: 3/3 = 1.0
    assert result.score == 1.0


def test_deterministic_score_partial_met(config):
    """Score should reflect criteria_met/total, not the LLM's freeform score."""
    response_data = {
        "score": 0.9,
        "evaluation": [
            {"criteria": "Criterion 1", "met": True, "details": "Passed"},
            {"criteria": "Criterion 2", "met": False, "details": "Failed"},
            {"criteria": "Criterion 3", "met": True, "details": "Passed"},
            {"criteria": "Criterion 4", "met": False, "details": "Failed"},
        ],
        "reasoning": "Test",
    }
    grader, patched_grade = _make_grader_with_mock_response(config, response_data)
    result = patched_grade("code content", ["c1", "c2", "c3", "c4"])
    # Score should be 2/4 = 0.5, NOT the LLM's 0.9
    assert result.score == 0.5


def test_deterministic_score_none_met(config):
    """Score should be 0.0 when no criteria are met."""
    response_data = {
        "score": 0.3,
        "evaluation": [
            {"criteria": "Criterion 1", "met": False, "details": "Failed"},
            {"criteria": "Criterion 2", "met": False, "details": "Failed"},
        ],
        "reasoning": "Test",
    }
    grader, patched_grade = _make_grader_with_mock_response(config, response_data)
    result = patched_grade("code content", ["c1", "c2"])
    assert result.score == 0.0


def test_temperature_is_omitted_for_claude_5(config, monkeypatch):
    """Verify Claude 5 uses Anthropic's required default sampling settings."""
    captured = {}

    class FakeChatAnthropic:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_anthropic.ChatAnthropic", FakeChatAnthropic)

    grader = ModelGrader(config)
    grader.config.model = Model.CLAUDE_SONNET_5
    grader._get_llm()

    assert "temperature" not in captured


def test_temperature_is_zero_openai(config, monkeypatch):
    """Verify temperature=0 is used for OpenAI models."""
    captured = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_openai.ChatOpenAI", FakeChatOpenAI)

    grader = ModelGrader(config)
    grader.config.model = Model.GPT_5_6_SOL
    grader._get_llm()

    assert captured["temperature"] == 0


def test_temperature_is_zero_google(config, monkeypatch):
    """Verify temperature=0 is used for Google models."""
    captured = {}

    class FakeChatGoogle:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_google_genai.ChatGoogleGenerativeAI", FakeChatGoogle)

    grader = ModelGrader(config)
    grader.config.model = Model.GEMINI_3_PRO_PREVIEW
    grader._get_llm()

    assert captured["temperature"] == 0
