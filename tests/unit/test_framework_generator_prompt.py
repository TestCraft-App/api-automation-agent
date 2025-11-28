"""Unit tests for check_and_prompt_for_existing_endpoints in FrameworkGenerator."""

from unittest.mock import Mock, patch

import pytest

from src.configuration.config import Config, Envs
from src.framework_generator import FrameworkGenerator
from src.models.api_definition import APIDefinition
from src.models.api_path import APIPath
from src.models.api_verb import APIVerb
from src.processors.api_processor import APIProcessor
from src.services.command_service import CommandService
from src.services.file_service import FileService
from src.services.llm_service import LLMService
from src.models.framework_state import FrameworkState


@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary config for testing."""
    return Config(destination_folder=str(tmp_path), env=Envs.DEV, override=False, use_existing_framework=True)


@pytest.fixture
def mock_api_processor():
    """Create a mock API processor."""
    processor = Mock(spec=APIProcessor)
    return processor


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    return Mock(spec=LLMService)


@pytest.fixture
def mock_command_service():
    """Create a mock command service."""
    return Mock(spec=CommandService)


@pytest.fixture
def file_service():
    """Create a FileService instance."""
    return FileService()


@pytest.fixture
def generator(temp_config, mock_llm_service, mock_command_service, file_service, mock_api_processor):
    """Create a FrameworkGenerator instance."""
    return FrameworkGenerator(
        config=temp_config,
        llm_service=mock_llm_service,
        command_service=mock_command_service,
        file_service=file_service,
        api_processor=mock_api_processor,
    )


@pytest.fixture
def api_definition():
    """Create a mock API definition."""
    return Mock(spec=APIDefinition)


class TestCheckAndPromptForExistingEndpoints:
    """Test check_and_prompt_for_existing_endpoints method."""

    def test_no_existing_endpoints_returns_early(
        self, generator, api_definition, mock_api_processor, monkeypatch
    ):
        """Test returns early when no existing paths/verbs without prompting user."""
        # Setup: no existing endpoints in state
        generator.state_manager._framework_state = FrameworkState()

        # Mock API processor to return empty lists (no paths/verbs to check)
        mock_api_processor.get_api_paths.return_value = []
        mock_api_processor.get_api_verbs.return_value = []

        # Track if input was called (it shouldn't be)
        input_called = []

        def mock_input(prompt):
            input_called.append(prompt)
            return "1"

        monkeypatch.setattr("builtins.input", mock_input)

        # Execute - should return immediately without user interaction
        with patch.object(generator.logger, "info") as mock_info:
            generator.check_and_prompt_for_existing_endpoints(api_definition)

            assert len(input_called) == 0, "Function should not prompt user when no existing endpoints"

            # Verify no warning messages about existing endpoints
            info_calls = [str(call) for call in mock_info.call_args_list]
            assert not any("already exist" in str(call) for call in info_calls)

        # Verify config remains unchanged
        assert generator.config.override is False

    def test_user_option_1_override(self, generator, api_definition, mock_api_processor, monkeypatch):
        """Test user option 1 sets override mode."""
        # Setup: existing endpoint in state
        state = FrameworkState()
        state.update_models(path="/users", models=[], auto_save=False)
        generator.state_manager._framework_state = state

        # Mock API processor
        path = Mock(spec=APIPath)
        mock_api_processor.get_api_paths.return_value = [path]
        mock_api_processor.get_api_verbs.return_value = []
        mock_api_processor.get_api_path_name.return_value = "/users"
        mock_api_processor.get_api_verb_rootpath.return_value = None

        # Mock user input to return "1"
        input_calls = []

        def mock_input(prompt):
            input_calls.append(prompt)
            return "1"

        monkeypatch.setattr("builtins.input", mock_input)

        with patch.object(generator.logger, "info") as mock_info:
            generator.check_and_prompt_for_existing_endpoints(api_definition)

            # Verify override set
            assert generator.config.override is True

            # Verify info messages logged
            assert mock_info.called

    def test_user_option_2_skip(self, generator, api_definition, mock_api_processor, monkeypatch):
        """Test user option 2 enables skip mode."""
        # Setup: existing endpoint in state
        state = FrameworkState()
        state.update_models(path="/users", models=[], auto_save=False)
        generator.state_manager._framework_state = state

        # Mock API processor
        path = Mock(spec=APIPath)
        mock_api_processor.get_api_paths.return_value = [path]
        mock_api_processor.get_api_verbs.return_value = []
        mock_api_processor.get_api_path_name.return_value = "/users"
        mock_api_processor.get_api_verb_rootpath.return_value = None

        # Mock user input to return "2"
        def mock_input(prompt):
            return "2"

        monkeypatch.setattr("builtins.input", mock_input)

        with patch.object(generator.logger, "info") as mock_info:
            generator.check_and_prompt_for_existing_endpoints(api_definition)

            # Verify override remains False (skip mode)
            assert generator.config.override is False

            # Verify info messages logged
            assert mock_info.called

    def test_user_option_3_exit(self, generator, api_definition, mock_api_processor, monkeypatch):
        """Test user option 3 exits the program."""
        # Setup: existing endpoint in state
        state = FrameworkState()
        state.update_models(path="/users", models=[], auto_save=False)
        generator.state_manager._framework_state = state

        # Mock API processor
        path = Mock(spec=APIPath)
        mock_api_processor.get_api_paths.return_value = [path]
        mock_api_processor.get_api_verbs.return_value = []
        mock_api_processor.get_api_path_name.return_value = "/users"
        mock_api_processor.get_api_verb_rootpath.return_value = None

        # Mock user input to return "3"
        def mock_input(prompt):
            return "3"

        monkeypatch.setattr("builtins.input", mock_input)

        with patch.object(generator.logger, "info") as mock_info:
            with pytest.raises(SystemExit) as exc_info:
                generator.check_and_prompt_for_existing_endpoints(api_definition)

            # Verify exit code is 1
            assert exc_info.value.code == 1

            # Verify exit message logged
            assert mock_info.called

    def test_invalid_input_then_valid(self, generator, api_definition, mock_api_processor, monkeypatch):
        """Test prompts again on invalid input, then accepts valid input."""
        # Setup: existing endpoint in state
        state = FrameworkState()
        state.update_models(path="/users", models=[], auto_save=False)
        generator.state_manager._framework_state = state

        # Mock API processor
        path = Mock(spec=APIPath)
        mock_api_processor.get_api_paths.return_value = [path]
        mock_api_processor.get_api_verbs.return_value = []
        mock_api_processor.get_api_path_name.return_value = "/users"
        mock_api_processor.get_api_verb_rootpath.return_value = None

        # Mock user input: first invalid, then valid
        input_values = ["invalid", "5", "abc", "1"]
        input_index = [0]

        def mock_input(prompt):
            if input_index[0] < len(input_values):
                value = input_values[input_index[0]]
                input_index[0] += 1
                return value
            return "1"

        monkeypatch.setattr("builtins.input", mock_input)

        with patch.object(generator.logger, "warning") as mock_warning:
            generator.check_and_prompt_for_existing_endpoints(api_definition)

            # Verify warnings for invalid input
            assert mock_warning.called

            # Verify override set after valid input
            assert generator.config.override is True

    def test_displays_existing_paths_correctly(
        self, generator, api_definition, mock_api_processor, monkeypatch
    ):
        """Test displays existing paths correctly."""
        # Setup: existing endpoint in state
        state = FrameworkState()
        state.update_models(path="/users", models=[], auto_save=False)
        generator.state_manager._framework_state = state

        # Mock API processor
        path = Mock(spec=APIPath)
        mock_api_processor.get_api_paths.return_value = [path]
        mock_api_processor.get_api_verbs.return_value = []
        mock_api_processor.get_api_path_name.return_value = "/users"
        mock_api_processor.get_api_verb_rootpath.return_value = None

        # Mock user input
        def mock_input(prompt):
            return "1"

        monkeypatch.setattr("builtins.input", mock_input)

        with patch.object(generator.logger, "info") as mock_info:
            generator.check_and_prompt_for_existing_endpoints(api_definition)

            # Verify path displayed in info messages
            info_calls = [str(call) for call in mock_info.call_args_list]
            assert any("/users" in str(call) for call in info_calls)

    def test_displays_existing_verbs_correctly(
        self, generator, api_definition, mock_api_processor, monkeypatch
    ):
        """Test displays existing verbs correctly."""
        # Setup: existing verb in state
        state = FrameworkState()
        verb = APIVerb(path="/users", verb="get", root_path="/users", yaml={})
        state.update_tests(verb, ["test.ts"], auto_save=False)
        generator.state_manager._framework_state = state

        # Mock API processor
        mock_api_processor.get_api_paths.return_value = []
        mock_api_processor.get_api_verbs.return_value = [verb]
        mock_api_processor.get_api_path_name.return_value = "/users"
        mock_api_processor.get_api_verb_rootpath.return_value = "/users"

        # Mock user input
        def mock_input(prompt):
            return "1"

        monkeypatch.setattr("builtins.input", mock_input)

        with patch.object(generator.logger, "info") as mock_info:
            generator.check_and_prompt_for_existing_endpoints(api_definition)

            # Verify verb displayed in info messages
            info_calls = [str(call) for call in mock_info.call_args_list]
            assert any("GET" in str(call) or "/users" in str(call) for call in info_calls)

    def test_displays_paths_without_verbs(self, generator, api_definition, mock_api_processor, monkeypatch):
        """Test displays paths without verbs correctly."""
        # Setup: existing endpoint with models but no verbs
        state = FrameworkState()
        state.update_models(path="/users", models=[], auto_save=False)
        generator.state_manager._framework_state = state

        # Mock API processor
        path = Mock(spec=APIPath)
        mock_api_processor.get_api_paths.return_value = [path]
        mock_api_processor.get_api_verbs.return_value = []
        mock_api_processor.get_api_path_name.return_value = "/users"
        mock_api_processor.get_api_verb_rootpath.return_value = None

        # Mock user input
        def mock_input(prompt):
            return "1"

        monkeypatch.setattr("builtins.input", mock_input)

        with patch.object(generator.logger, "info") as mock_info:
            generator.check_and_prompt_for_existing_endpoints(api_definition)

            # Verify path displayed (without verb list)
            info_calls = [str(call) for call in mock_info.call_args_list]
            assert any("/users" in str(call) for call in info_calls)

    def test_mixed_paths_and_verbs(self, generator, api_definition, mock_api_processor, monkeypatch):
        """Test handles mixed scenario with both paths and verbs."""
        # Setup: existing endpoint with models and verbs
        state = FrameworkState()
        state.update_models(path="/users", models=[], auto_save=False)
        verb1 = APIVerb(path="/users", verb="get", root_path="/users", yaml={})
        verb2 = APIVerb(path="/orders", verb="post", root_path="/orders", yaml={})
        state.update_tests(verb1, ["test1.ts"], auto_save=False)
        state.update_tests(verb2, ["test2.ts"], auto_save=False)
        generator.state_manager._framework_state = state

        # Mock API processor
        path1 = Mock(spec=APIPath)
        path2 = Mock(spec=APIPath)

        def get_path_name(path):
            if path == path1:
                return "/users"
            return "/orders"

        mock_api_processor.get_api_paths.return_value = [path1, path2]
        mock_api_processor.get_api_verbs.return_value = [verb1, verb2]
        mock_api_processor.get_api_path_name.side_effect = get_path_name
        mock_api_processor.get_api_verb_rootpath.side_effect = lambda v: v.root_path

        # Mock user input
        def mock_input(prompt):
            return "1"

        monkeypatch.setattr("builtins.input", mock_input)

        with patch.object(generator.logger, "info") as mock_info:
            generator.check_and_prompt_for_existing_endpoints(api_definition)

            # Verify both paths and verbs are displayed
            info_calls = [str(call) for call in mock_info.call_args_list]
            assert any("/users" in str(call) for call in info_calls)
            assert any("/orders" in str(call) for call in info_calls)
