import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from src.utils.interactive_setup import InteractiveSetup


class TestInteractiveSetupIntegration:
    """Integration tests for the interactive setup functionality."""

    def setup_method(self):
        """Set up test environment with temporary directory."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.example_env = self.test_dir / "example.env"
        self.env_file = self.test_dir / ".env"

        self.example_env.write_text(
            """# Example environment configuration
MODEL=claude-sonnet-4-20250514
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
DEBUG=False
LANGCHAIN_DEBUG=False
"""
        )

    def teardown_method(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_check_env_file_missing(self, mock_get_dir):
        """Test env file check when no .env file exists."""
        mock_get_dir.return_value = self.test_dir

        result = InteractiveSetup.check_env_file()

        assert result is False

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_check_env_file_empty(self, mock_get_dir):
        """Test env file check when .env file is empty."""
        mock_get_dir.return_value = self.test_dir
        self.env_file.write_text("")

        result = InteractiveSetup.check_env_file()

        assert result is False

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_check_env_file_valid_openai(self, mock_get_dir):
        """Test env file check with valid OpenAI key."""
        mock_get_dir.return_value = self.test_dir
        self.env_file.write_text("OPENAI_API_KEY=sk-test-key\n")

        result = InteractiveSetup.check_env_file()

        assert result is True

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_check_env_file_valid_anthropic(self, mock_get_dir):
        """Test env file check with valid Anthropic key."""
        mock_get_dir.return_value = self.test_dir
        self.env_file.write_text("ANTHROPIC_API_KEY=sk-ant-test-key\n")

        result = InteractiveSetup.check_env_file()

        assert result is True

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_copy_example_env_success(self, mock_get_dir):
        """Test successful copying of example.env to .env."""
        mock_get_dir.return_value = self.test_dir

        with patch("builtins.print"):
            result = InteractiveSetup.copy_example_env()

        assert result is True
        assert self.env_file.exists()
        assert self.env_file.read_text() == self.example_env.read_text()

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_copy_example_env_missing_source(self, mock_get_dir):
        """Test handling when example.env doesn't exist."""
        empty_dir = Path(tempfile.mkdtemp())
        mock_get_dir.return_value = empty_dir

        try:
            with patch("builtins.print"):
                result = InteractiveSetup.copy_example_env()

            assert result is False
        finally:
            shutil.rmtree(empty_dir)

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_update_env_file_new_file(self, mock_get_dir):
        """Test updating env file when file doesn't exist."""
        mock_get_dir.return_value = self.test_dir
        provider = InteractiveSetup.SUPPORTED_PROVIDERS["2"]

        with patch("builtins.print"):
            result = InteractiveSetup.update_env_file(provider, "gpt-5-mini", {"OPENAI_API_KEY": "test-key"})

        assert result is True
        content = self.env_file.read_text()
        assert "OPENAI_API_KEY=test-key" in content
        assert "MODEL=gpt-5-mini" in content

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_update_env_file_existing_file(self, mock_get_dir):
        """Test updating existing env file."""
        mock_get_dir.return_value = self.test_dir

        self.env_file.write_text(
            """OPENAI_API_KEY=old-key
MODEL=gpt-3.5-turbo
DEBUG=False
"""
        )

        provider = InteractiveSetup.SUPPORTED_PROVIDERS["2"]

        with patch("builtins.print"):
            result = InteractiveSetup.update_env_file(provider, "gpt-5-mini", {"OPENAI_API_KEY": "new-key"})

        assert result is True
        content = self.env_file.read_text()
        assert "OPENAI_API_KEY=new-key" in content
        assert "MODEL=gpt-5-mini" in content
        assert "old-key" not in content
        assert "DEBUG=False" in content

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_update_env_file_anthropic_provider(self, mock_get_dir):
        """Test updating env file with Anthropic provider."""
        mock_get_dir.return_value = self.test_dir
        provider = InteractiveSetup.SUPPORTED_PROVIDERS["1"]

        with patch("builtins.print"):
            result = InteractiveSetup.update_env_file(
                provider, "claude-sonnet-4-20250514", {"ANTHROPIC_API_KEY": "sk-ant-key"}
            )

        assert result is True
        content = self.env_file.read_text()
        assert "ANTHROPIC_API_KEY=sk-ant-key" in content
        assert "MODEL=claude-sonnet-4-20250514" in content

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_update_env_file_bedrock_provider(self, mock_get_dir):
        """Test updating env file with AWS Bedrock provider."""
        mock_get_dir.return_value = self.test_dir
        provider = InteractiveSetup.SUPPORTED_PROVIDERS["4"]

        credentials = {
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "AWS_REGION": "eu-west-1",
        }

        with patch("builtins.print"):
            result = InteractiveSetup.update_env_file(provider, "openai.gpt-5.1", credentials)

        assert result is True
        content = self.env_file.read_text()
        assert "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE" in content
        assert "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" in content
        assert "AWS_REGION=eu-west-1" in content
        assert "MODEL=openai.gpt-5.1" in content

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_complete_setup_flow_openai(self, mock_get_dir):
        """Test complete setup flow for OpenAI provider."""
        mock_get_dir.return_value = self.test_dir

        def mock_api_key_input(prompt):
            return "sk-test-openai-key"

        with patch("builtins.input", side_effect=["2", ""]):
            with patch("builtins.print"):
                result = InteractiveSetup.run_interactive_setup(input_func=mock_api_key_input)

        assert result is True
        assert self.env_file.exists()

        content = self.env_file.read_text()
        assert "OPENAI_API_KEY=sk-test-openai-key" in content
        assert "MODEL=gpt-5.2" in content

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_complete_setup_flow_anthropic(self, mock_get_dir):
        """Test complete setup flow for Anthropic provider."""
        mock_get_dir.return_value = self.test_dir

        def mock_api_key_input(prompt):
            return "sk-ant-test-key"

        with patch("builtins.input", side_effect=["1", "1"]):
            with patch("builtins.print"):
                result = InteractiveSetup.run_interactive_setup(input_func=mock_api_key_input)

        assert result is True
        assert self.env_file.exists()

        content = self.env_file.read_text()
        assert "ANTHROPIC_API_KEY=sk-ant-test-key" in content
        assert "MODEL=claude-sonnet-4-5-20250929" in content

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_complete_setup_flow_bedrock(self, mock_get_dir):
        """Test complete setup flow for AWS Bedrock provider."""
        mock_get_dir.return_value = self.test_dir

        # Mock inputs for AWS credentials: access key, secret key, region
        def mock_credentials_input(prompt):
            if "Access Key ID" in prompt:
                return "AKIAIOSFODNN7EXAMPLE"
            elif "Secret Access Key" in prompt:
                return "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            return ""

        with patch("builtins.input", side_effect=["4", "", "us-west-2"]):
            with patch("builtins.print"):
                result = InteractiveSetup.run_interactive_setup(input_func=mock_credentials_input)

        assert result is True
        assert self.env_file.exists()

        content = self.env_file.read_text()
        assert "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE" in content
        assert "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" in content
        assert "AWS_REGION=us-west-2" in content
        assert "MODEL=anthropic.claude-sonnet-4-5-20250929-v1:0" in content

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_complete_setup_flow_bedrock_aws_cli(self, mock_get_dir):
        """Test complete setup flow for AWS Bedrock with AWS CLI authentication."""
        mock_get_dir.return_value = self.test_dir

        # Mock skipping credentials (pressing Enter) to use AWS CLI
        def mock_credentials_input(prompt):
            return ""  # Skip credential input

        with patch("builtins.input", side_effect=["4", "", "eu-central-1"]):
            with patch("builtins.print"):
                result = InteractiveSetup.run_interactive_setup(input_func=mock_credentials_input)

        assert result is True
        assert self.env_file.exists()

        content = self.env_file.read_text()
        # Should only have region, no access keys
        assert "AWS_REGION=eu-central-1" in content
        assert "AWS_ACCESS_KEY_ID" not in content or "AWS_ACCESS_KEY_ID=" in content
        assert "MODEL=anthropic.claude-sonnet-4-5-20250929-v1:0" in content

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_complete_setup_flow_invalid_provider_then_valid(self, mock_get_dir):
        """Test setup flow with invalid provider input then valid input."""
        mock_get_dir.return_value = self.test_dir

        def mock_api_key_input(prompt):
            return "sk-test-key"

        with patch("builtins.input", side_effect=["5", "1", ""]):
            with patch("builtins.print"):
                result = InteractiveSetup.run_interactive_setup(input_func=mock_api_key_input)

        assert result is True
        content = self.env_file.read_text()
        assert "ANTHROPIC_API_KEY=sk-test-key" in content

    @patch.object(InteractiveSetup, "get_executable_directory")
    def test_setup_failure_no_example_env(self, mock_get_dir):
        """Test setup failure when example.env is missing."""
        empty_dir = Path(tempfile.mkdtemp())
        mock_get_dir.return_value = empty_dir

        try:
            with patch("builtins.print"):
                result = InteractiveSetup.run_interactive_setup()

            assert result is False
        finally:
            shutil.rmtree(empty_dir)


class TestInteractiveSetupConfiguration:
    """Tests for interactive setup configuration validation."""

    def test_provider_configuration_structure(self):
        """Test that provider configurations have correct structure."""
        providers = InteractiveSetup.SUPPORTED_PROVIDERS

        assert isinstance(providers, dict)
        assert len(providers) == 4
        assert "1" in providers
        assert "2" in providers
        assert "3" in providers
        assert "4" in providers

    def test_openai_provider_configuration(self):
        """Test OpenAI provider configuration."""
        openai_config = InteractiveSetup.SUPPORTED_PROVIDERS["2"]

        assert openai_config["name"] == "OpenAI"
        assert openai_config["env_key"] == "OPENAI_API_KEY"
        assert len(openai_config["models"]) > 0
        assert openai_config["default_model"] in openai_config["models"]
        assert "gpt-5-mini" in openai_config["models"]

    def test_anthropic_provider_configuration(self):
        """Test Anthropic provider configuration."""
        anthropic_config = InteractiveSetup.SUPPORTED_PROVIDERS["1"]

        assert anthropic_config["name"] == "Anthropic (recommended)"
        assert anthropic_config["env_key"] == "ANTHROPIC_API_KEY"
        assert len(anthropic_config["models"]) > 0
        assert anthropic_config["default_model"] in anthropic_config["models"]
        assert "claude-sonnet-4-20250514" in anthropic_config["models"]

    def test_bedrock_provider_configuration(self):
        """Test AWS Bedrock provider configuration."""
        bedrock_config = InteractiveSetup.SUPPORTED_PROVIDERS["4"]

        assert bedrock_config["name"] == "AWS Bedrock"
        assert bedrock_config["env_key"] == "AWS_ACCESS_KEY_ID"
        assert "additional_keys" in bedrock_config
        assert "AWS_SECRET_ACCESS_KEY" in bedrock_config["additional_keys"]
        assert "AWS_REGION" in bedrock_config["additional_keys"]
        assert len(bedrock_config["models"]) > 0
        assert bedrock_config["default_model"] in bedrock_config["models"]
        assert "anthropic.claude-sonnet-4-5-20250929-v1:0" in bedrock_config["models"]
        assert "openai.gpt-5.2" in bedrock_config["models"]

    def test_get_executable_directory_returns_path(self):
        """Test that get_executable_directory returns a valid path."""
        result = InteractiveSetup.get_executable_directory()

        assert isinstance(result, Path)
        assert result.exists()
