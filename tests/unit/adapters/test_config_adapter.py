"""Unit tests for config_adapter module."""

import os
from unittest.mock import patch, MagicMock
import pytest

from src.adapters.config_adapter import BaseConfigAdapter, DevConfigAdapter, ProdConfigAdapter
from src.configuration.config import Envs
from src.configuration.models import Model


class TestBaseConfigAdapter:
    """Tests for BaseConfigAdapter.get_base_config method."""

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "MODEL": "claude-sonnet-4-20250514",
            "DEBUG": "True",
            "LANGCHAIN_DEBUG": "True",
            "ANTHROPIC_API_KEY": "sk-ant-test-key",
            "OPENAI_API_KEY": "sk-openai-test-key",
            "GOOGLE_API_KEY": "google-test-key",
            "DESTINATION_FOLDER": "/custom/path",
        },
        clear=True,
    )
    def test_get_base_config_with_all_env_vars(self, mock_load_dotenv, mock_set_debug):
        """Test config loading with all environment variables set."""
        config = BaseConfigAdapter.get_base_config(Envs.DEV)

        assert config.env == Envs.DEV
        assert config.model == Model.CLAUDE_SONNET_4
        assert config.debug is True
        assert config.langchain_debug is True
        assert config.anthropic_api_key == "sk-ant-test-key"
        assert config.openai_api_key == "sk-openai-test-key"
        assert config.google_api_key == "google-test-key"
        assert config.destination_folder == "/custom/path"

        mock_load_dotenv.assert_called_once_with(override=True)
        mock_set_debug.assert_called_once_with(True)

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_base_config_with_defaults(self, mock_load_dotenv, mock_set_debug):
        """Test config loading with default values when no env vars are set."""
        config = BaseConfigAdapter.get_base_config(Envs.PROD)

        assert config.env == Envs.PROD
        assert config.model == Model.CLAUDE_SONNET_4_5
        assert config.debug is False
        assert config.langchain_debug is False
        assert config.anthropic_api_key == ""
        assert config.openai_api_key == ""
        assert config.google_api_key == ""
        assert config.destination_folder.startswith("./generated/generated-framework_")

        mock_load_dotenv.assert_called_once_with(override=True)
        mock_set_debug.assert_called_once_with(False)

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "MODEL": "gpt-5.1",
            "DEBUG": "false",
            "LANGCHAIN_DEBUG": "False",
        },
        clear=True,
    )
    def test_get_base_config_with_openai_model(self, mock_load_dotenv, mock_set_debug):
        """Test config loading with OpenAI model."""
        config = BaseConfigAdapter.get_base_config(Envs.DEV)

        assert config.model == Model.GPT_5_1
        assert config.debug is False
        assert config.langchain_debug is False

        mock_set_debug.assert_called_once_with(False)

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "MODEL": "gemini-3-pro-preview",
            "GOOGLE_API_KEY": "test-google-key",
        },
        clear=True,
    )
    def test_get_base_config_with_google_model(self, mock_load_dotenv, mock_set_debug):
        """Test config loading with Google Gemini model."""
        config = BaseConfigAdapter.get_base_config(Envs.DEV)

        assert config.model == Model.GEMINI_3_PRO_PREVIEW
        assert config.google_api_key == "test-google-key"

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "DEBUG": "true",
            "LANGCHAIN_DEBUG": "TRUE",
        },
        clear=True,
    )
    def test_get_base_config_debug_flags_case_insensitive(self, mock_load_dotenv, mock_set_debug):
        """Test that debug flags work with various capitalizations."""
        config = BaseConfigAdapter.get_base_config(Envs.DEV)

        assert config.debug is True
        assert config.langchain_debug is True

        mock_set_debug.assert_called_once_with(True)

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "MODEL": "claude-haiku-4-5-20251001",
            "ANTHROPIC_API_KEY": "sk-ant-haiku-key",
        },
        clear=True,
    )
    def test_get_base_config_with_haiku_model(self, mock_load_dotenv, mock_set_debug):
        """Test config loading with Claude Haiku model."""
        config = BaseConfigAdapter.get_base_config(Envs.PROD)

        assert config.env == Envs.PROD
        assert config.model == Model.CLAUDE_HAIKU_4_5
        assert config.anthropic_api_key == "sk-ant-haiku-key"

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "MODEL": "gpt-5-mini",
            "OPENAI_API_KEY": "sk-openai-mini-key",
        },
        clear=True,
    )
    def test_get_base_config_with_gpt_mini_model(self, mock_load_dotenv, mock_set_debug):
        """Test config loading with GPT-5 Mini model."""
        config = BaseConfigAdapter.get_base_config(Envs.DEV)

        assert config.model == Model.GPT_5_MINI
        assert config.openai_api_key == "sk-openai-mini-key"

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GOOGLE_API_KEY": "",
        },
        clear=True,
    )
    def test_get_base_config_with_empty_api_keys(self, mock_load_dotenv, mock_set_debug):
        """Test config loading with explicitly empty API keys."""
        config = BaseConfigAdapter.get_base_config(Envs.DEV)

        assert config.anthropic_api_key == ""
        assert config.openai_api_key == ""
        assert config.google_api_key == ""

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch("src.adapters.config_adapter.datetime")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_base_config_destination_folder_format(self, mock_datetime, mock_load_dotenv, mock_set_debug):
        """Test that destination folder has correct timestamp format."""
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20251120-153000"
        mock_datetime.now.return_value = mock_now

        config = BaseConfigAdapter.get_base_config(Envs.DEV)

        assert config.destination_folder == "./generated/generated-framework_20251120-153000"
        mock_now.strftime.assert_called_once_with("%Y%m%d-%H%M%S")


class TestDevConfigAdapter:
    """Tests for DevConfigAdapter."""

    def test_dev_config_adapter_is_subclass(self):
        """Test that DevConfigAdapter inherits from BaseConfigAdapter."""
        assert issubclass(DevConfigAdapter, BaseConfigAdapter)

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(os.environ, {"MODEL": "claude-sonnet-4-5-20250929"}, clear=True)
    def test_dev_config_adapter_singleton(self, mock_load_dotenv, mock_set_debug):
        """Test that DevConfigAdapter uses singleton provider."""
        adapter = DevConfigAdapter()
        config1 = adapter.config()
        config2 = adapter.config()

        # Singleton should return the same instance
        assert config1 is config2
        assert config1.env == Envs.DEV


class TestProdConfigAdapter:
    """Tests for ProdConfigAdapter."""

    def test_prod_config_adapter_is_subclass(self):
        """Test that ProdConfigAdapter inherits from BaseConfigAdapter."""
        assert issubclass(ProdConfigAdapter, BaseConfigAdapter)

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(os.environ, {"MODEL": "gpt-5"}, clear=True)
    def test_prod_config_adapter_singleton(self, mock_load_dotenv, mock_set_debug):
        """Test that ProdConfigAdapter uses singleton provider."""
        adapter = ProdConfigAdapter()
        config1 = adapter.config()
        config2 = adapter.config()

        # Singleton should return the same instance
        assert config1 is config2
        assert config1.env == Envs.PROD


class TestConfigAdapterEdgeCases:
    """Tests for edge cases and error conditions."""

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "DEBUG": "invalid",
            "LANGCHAIN_DEBUG": "not_a_bool",
        },
        clear=True,
    )
    def test_get_base_config_invalid_boolean_values(self, mock_load_dotenv, mock_set_debug):
        """Test that invalid boolean values default to False."""
        config = BaseConfigAdapter.get_base_config(Envs.DEV)

        # .title() on "invalid" becomes "Invalid", which != "True"
        assert config.debug is False
        assert config.langchain_debug is False

        mock_set_debug.assert_called_once_with(False)

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "MODEL": "invalid-model-name",
        },
        clear=True,
    )
    def test_get_base_config_invalid_model_raises_error(self, mock_load_dotenv, mock_set_debug):
        """Test that invalid model name raises ValueError."""
        with pytest.raises(ValueError):
            BaseConfigAdapter.get_base_config(Envs.DEV)

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "DESTINATION_FOLDER": "",
        },
        clear=True,
    )
    def test_get_base_config_empty_destination_folder(self, mock_load_dotenv, mock_set_debug):
        """Test that empty DESTINATION_FOLDER env var is preserved as empty string."""
        config = BaseConfigAdapter.get_base_config(Envs.DEV)

        # os.getenv returns empty string when env var is set to empty
        assert config.destination_folder == ""

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "MODEL": "anthropic.claude-sonnet-4-5-20250929-v1:0",
            "AWS_ACCESS_KEY_ID": "test-access-key-id",
            "AWS_SECRET_ACCESS_KEY": "test-secret-access-key",
            "AWS_REGION": "us-west-2",
        },
        clear=True,
    )
    def test_get_base_config_with_bedrock_credentials(self, mock_load_dotenv, mock_set_debug):
        """Test config loading with AWS Bedrock credentials."""
        config = BaseConfigAdapter.get_base_config(Envs.DEV)

        assert config.model == Model.BEDROCK_CLAUDE_SONNET_4_5
        assert config.aws_access_key_id == "test-access-key-id"
        assert config.aws_secret_access_key == "test-secret-access-key"
        assert config.aws_region == "us-west-2"

    @patch("src.adapters.config_adapter.set_debug")
    @patch("src.adapters.config_adapter.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "MODEL": "openai.gpt-5.1",
        },
        clear=True,
    )
    def test_get_base_config_with_bedrock_model_defaults(self, mock_load_dotenv, mock_set_debug):
        """Test that AWS region defaults to us-east-1 when not specified."""
        config = BaseConfigAdapter.get_base_config(Envs.DEV)

        assert config.model == Model.BEDROCK_GPT_5_1
        assert config.aws_access_key_id == ""
        assert config.aws_secret_access_key == ""
        assert config.aws_region == "us-east-1"
