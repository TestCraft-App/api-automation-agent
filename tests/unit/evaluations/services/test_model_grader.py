"""Unit tests for ModelGrader service."""

import pytest
from unittest.mock import MagicMock

from evaluations.services.model_grader import ModelGrader
from src.configuration.config import Config
from src.configuration.models import Model


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(
        openai_api_key="test-openai-key",
        anthropic_api_key="test-anthropic-key",
        google_api_key="test-google-key",
        aws_access_key_id="test-access-key",
        aws_secret_access_key="test-secret-key",
        aws_region="us-west-2",
        model=Model.CLAUDE_SONNET_4_5,
        destination_folder="test-folder",
        debug=False,
        langchain_debug=False,
    )


@pytest.fixture
def grader(config):
    """Create a ModelGrader instance."""
    return ModelGrader(config)


def test_get_llm_anthropic(grader, monkeypatch):
    """Test LLM initialization for Anthropic models."""
    captured = {}

    class FakeChatAnthropic:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_anthropic.ChatAnthropic", FakeChatAnthropic)

    grader.config.model = Model.CLAUDE_SONNET_4_5
    llm = grader._get_llm()

    assert isinstance(llm, FakeChatAnthropic)
    assert captured["model_name"] == Model.CLAUDE_SONNET_4_5.value


def test_get_llm_google(grader, monkeypatch):
    """Test LLM initialization for Google models."""
    captured = {}

    class FakeChatGoogle:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_google_genai.ChatGoogleGenerativeAI", FakeChatGoogle)

    grader.config.model = Model.GEMINI_3_PRO_PREVIEW
    llm = grader._get_llm()

    assert isinstance(llm, FakeChatGoogle)
    assert captured["model"] == Model.GEMINI_3_PRO_PREVIEW.value


def test_get_llm_openai(grader, monkeypatch):
    """Test LLM initialization for OpenAI models."""
    captured = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_openai.ChatOpenAI", FakeChatOpenAI)

    grader.config.model = Model.GPT_5_1
    llm = grader._get_llm()

    assert isinstance(llm, FakeChatOpenAI)
    assert captured["model"] == Model.GPT_5_1.value


def test_get_llm_bedrock_with_credentials(grader, monkeypatch):
    """Test LLM initialization for Bedrock models with explicit credentials."""
    captured = {}

    class FakeChatBedrock:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_aws.ChatBedrock", FakeChatBedrock)

    grader.config.model = Model.BEDROCK_CLAUDE_SONNET_4_5
    grader.config.aws_access_key_id = "test-access-key"
    grader.config.aws_secret_access_key = "test-secret-key"
    grader.config.aws_region = "eu-west-1"

    llm = grader._get_llm()

    assert isinstance(llm, FakeChatBedrock)
    assert captured["model_id"] == Model.BEDROCK_CLAUDE_SONNET_4_5.value
    assert captured["region_name"] == "eu-west-1"
    assert captured["aws_access_key_id"] == "test-access-key"
    assert captured["aws_secret_access_key"] == "test-secret-key"


def test_get_llm_bedrock_without_credentials(grader, monkeypatch):
    """Test LLM initialization for Bedrock models without explicit credentials (AWS CLI)."""
    captured = {}

    class FakeChatBedrock:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_aws.ChatBedrock", FakeChatBedrock)

    grader.config.model = Model.BEDROCK_CLAUDE_SONNET_4_5
    grader.config.aws_access_key_id = ""
    grader.config.aws_secret_access_key = ""
    grader.config.aws_region = "ap-southeast-2"

    llm = grader._get_llm()

    assert isinstance(llm, FakeChatBedrock)
    assert captured["model_id"] == Model.BEDROCK_CLAUDE_SONNET_4_5.value
    assert captured["region_name"] == "ap-southeast-2"
    assert "aws_access_key_id" not in captured
    assert "aws_secret_access_key" not in captured


def test_get_llm_bedrock_default_region(grader, monkeypatch):
    """Test LLM initialization for Bedrock models with default region."""
    captured = {}

    class FakeChatBedrock:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_aws.ChatBedrock", FakeChatBedrock)

    grader.config.model = Model.BEDROCK_GPT_5_1
    grader.config.aws_access_key_id = ""
    grader.config.aws_secret_access_key = ""
    grader.config.aws_region = ""

    llm = grader._get_llm()

    assert isinstance(llm, FakeChatBedrock)
    assert captured["region_name"] == "us-east-1"


def test_get_llm_uses_provided_llm(grader):
    """Test that _get_llm returns the provided LLM if one was passed to constructor."""
    mock_llm = MagicMock()
    grader_with_llm = ModelGrader(grader.config, llm=mock_llm)

    result = grader_with_llm._get_llm()

    assert result is mock_llm
