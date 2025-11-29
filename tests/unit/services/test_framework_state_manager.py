"""Unit tests for FrameworkStateManager service."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.configuration.config import Config, Envs
from src.models.api_verb import APIVerb
from src.models.generated_model import GeneratedModel
from src.services.file_service import FileService
from src.services.framework_state_manager import FrameworkStateManager
from src.models.framework_state import FrameworkState


@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary config for testing."""
    return Config(destination_folder=str(tmp_path), env=Envs.DEV, override=False)


@pytest.fixture
def file_service():
    """Create a FileService instance."""
    return FileService()


@pytest.fixture
def state_manager(temp_config, file_service):
    """Create a FrameworkStateManager instance."""
    return FrameworkStateManager(temp_config, file_service)


@pytest.fixture
def sample_models():
    """Create sample GeneratedModel objects."""
    return [
        GeneratedModel(
            path="src/models/requests/UserRequest.ts",
            fileContent="export interface UserRequest { name: string; }",
            summary="UserRequest model",
        ),
        GeneratedModel(
            path="src/models/services/UserService.ts",
            fileContent="export class UserService { }",
            summary="UserService service",
        ),
    ]


class TestFrameworkStateManagerInitialization:
    """Test FrameworkStateManager initialization."""

    def test_initialization(self, temp_config, file_service):
        """Test proper initialization with config and file_service."""
        manager = FrameworkStateManager(temp_config, file_service)
        assert manager.config == temp_config
        assert manager.file_service == file_service
        assert isinstance(manager._framework_state, FrameworkState)
        assert manager._state_loaded_models == {}

    def test_framework_state_initialized(self, state_manager):
        """Test framework state is initialized."""
        assert isinstance(state_manager._framework_state, FrameworkState)


class TestFrameworkStateManagerLoadState:
    """Test load_state() method."""

    def test_load_state_when_file_exists(self, state_manager, tmp_path, sample_models):
        """Test loading state from existing file."""
        state = FrameworkState(framework_root=tmp_path)
        state.update_models(path="/users", models=sample_models)

        for model in sample_models:
            model_path = tmp_path / model.path
            model_path.parent.mkdir(parents=True, exist_ok=True)
            model_path.write_text(model.fileContent, encoding="utf-8")

        def mock_read_file(path):
            model_path = Path(path)
            if model_path.exists():
                return model_path.read_text(encoding="utf-8")
            return None

        state_manager.file_service.read_file = Mock(side_effect=mock_read_file)

        state_manager.load_state()

        assert len(state_manager._framework_state.generated_endpoints) == 1
        assert state_manager.get_endpoint_state("/users") is not None
        assert len(state_manager._state_loaded_models) == 1

    def test_load_state_when_file_not_exists(self, state_manager, tmp_path):
        """Test loading state when file doesn't exist (creates empty state)."""
        state_manager.load_state()
        assert len(state_manager._framework_state.generated_endpoints) == 0
        assert len(state_manager._state_loaded_models) == 0

    def test_load_state_with_invalid_json(self, state_manager, tmp_path):
        """Test loading state with invalid JSON (graceful handling)."""
        state_file = tmp_path / FrameworkState.STATE_FILENAME
        state_file.write_text("{invalid json", encoding="utf-8")

        state_manager.load_state()
        # Should create empty state
        assert len(state_manager._framework_state.generated_endpoints) == 0

    def test_load_state_with_missing_model_files(self, state_manager, tmp_path, sample_models):
        """Test loading state when model files don't exist (warning logged)."""
        state = FrameworkState(framework_root=tmp_path)
        state.update_models(path="/users", models=sample_models)

        # Don't create model files - they're missing

        # Mock file_service.read_file to return None
        state_manager.file_service.read_file = Mock(return_value=None)

        with patch.object(state_manager.logger, "warning") as mock_warning:
            state_manager.load_state()
            # Should log warnings for missing files
            assert mock_warning.called

        # State should still be loaded, but no models in _state_loaded_models
        assert len(state_manager._framework_state.generated_endpoints) == 1
        assert len(state_manager._state_loaded_models) == 0

    def test_load_state_with_valid_model_files(self, state_manager, tmp_path, sample_models):
        """Test loading state with valid model files (models loaded correctly)."""
        # Create state file
        state = FrameworkState(framework_root=tmp_path)
        state.update_models(path="/users", models=sample_models)

        # Create model files
        for model in sample_models:
            model_path = tmp_path / model.path
            model_path.parent.mkdir(parents=True, exist_ok=True)
            model_path.write_text(model.fileContent, encoding="utf-8")

        # Mock file_service.read_file
        def mock_read_file(path):
            model_path = Path(path)
            if model_path.exists():
                return model_path.read_text(encoding="utf-8")
            return None

        state_manager.file_service.read_file = Mock(side_effect=mock_read_file)

        state_manager.load_state()

        # Verify models loaded
        assert len(state_manager._state_loaded_models) == 1
        model_info = state_manager._state_loaded_models["/users"]
        assert model_info.path == "/users"
        assert len(model_info.models) == 2
        assert len(model_info.files) == 2

    def test_load_state_with_multiple_endpoints(self, state_manager, tmp_path):
        """Test loading state with multiple endpoints."""
        # Create state with multiple endpoints
        state = FrameworkState(framework_root=tmp_path)
        models1 = [GeneratedModel(path="src/models/user.ts", fileContent="content1", summary="User")]
        models2 = [GeneratedModel(path="src/models/order.ts", fileContent="content2", summary="Order")]
        state.update_models(path="/users", models=models1)
        state.update_models(path="/orders", models=models2)

        # Create model files
        (tmp_path / "src" / "models").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "models" / "user.ts").write_text("content1", encoding="utf-8")
        (tmp_path / "src" / "models" / "order.ts").write_text("content2", encoding="utf-8")

        # Mock file_service.read_file
        def mock_read_file(path):
            model_path = Path(path)
            if model_path.exists():
                return model_path.read_text(encoding="utf-8")
            return None

        state_manager.file_service.read_file = Mock(side_effect=mock_read_file)

        state_manager.load_state()

        assert len(state_manager._state_loaded_models) == 2
        assert "/users" in state_manager._state_loaded_models
        assert "/orders" in state_manager._state_loaded_models


class TestFrameworkStateManagerGetPreloadedModelInfo:
    """Test get_preloaded_model_info() method."""

    def test_get_preloaded_model_info_empty(self, state_manager):
        """Test returning empty list when no models loaded."""
        result = state_manager.get_preloaded_model_info()
        assert result == []

    def test_get_preloaded_model_info_with_models(self, state_manager, tmp_path, sample_models):
        """Test returning correct ModelInfo objects."""
        # Setup state and load models
        state = FrameworkState(framework_root=tmp_path)
        state.update_models(path="/users", models=sample_models)

        for model in sample_models:
            model_path = tmp_path / model.path
            model_path.parent.mkdir(parents=True, exist_ok=True)
            model_path.write_text(model.fileContent, encoding="utf-8")

        def mock_read_file(path):
            model_path = Path(path)
            if model_path.exists():
                return model_path.read_text(encoding="utf-8")
            return None

        state_manager.file_service.read_file = Mock(side_effect=mock_read_file)
        state_manager.load_state()

        result = state_manager.get_preloaded_model_info()
        assert len(result) == 1
        assert result[0].path == "/users"
        assert len(result[0].models) == 2


class TestFrameworkStateManagerShouldGenerateModelsForPath:
    """Test should_generate_models_for_path() method."""

    def test_should_generate_when_path_not_exists(self, state_manager):
        """Test returning True when path doesn't exist in state."""
        result = state_manager.should_generate_models_for_path("/new-path")
        assert result is True

    def test_should_generate_when_path_exists_and_override_false(self, state_manager, tmp_path):
        """Test returning False when path exists and override is False."""
        state = FrameworkState(framework_root=tmp_path)
        state.update_models(path="/users", models=[])
        state_manager.load_state()

        result = state_manager.should_generate_models_for_path("/users")
        assert result is False

    def test_should_generate_when_path_exists_and_override_true(self, state_manager, tmp_path):
        """Test returning True when path exists and override is True."""
        state = FrameworkState(framework_root=tmp_path)
        state.update_models(path="/users", models=[])
        state_manager.load_state()

        state_manager.config.override = True
        with patch.object(state_manager.logger, "info") as mock_info:
            result = state_manager.should_generate_models_for_path("/users")
            assert result is True
            assert mock_info.called


class TestFrameworkStateManagerShouldGenerateTestsVerb:
    """Test should_generate_tests_verb() method."""

    def test_should_generate_when_verb_not_exists(self, state_manager):
        """Test returning True when verb doesn't exist in state."""
        verb = APIVerb(path="/users", verb="get", root_path="/users", yaml={})
        result = state_manager.should_generate_tests_verb(verb)
        assert result is True

    def test_should_generate_when_verb_exists_and_override_false(self, state_manager, tmp_path):
        """Test returning False when verb exists and override is False."""
        state = FrameworkState(framework_root=tmp_path)
        verb = APIVerb(path="/users", verb="get", root_path="/users", yaml={})
        state.update_tests(verb, ["test.ts"])
        state_manager.load_state()

        result = state_manager.should_generate_tests_verb(verb)
        assert result is False

    def test_should_generate_when_verb_exists_and_override_true(self, state_manager, tmp_path):
        """Test returning True when verb exists and override is True."""
        state = FrameworkState(framework_root=tmp_path)
        verb = APIVerb(path="/users", verb="get", root_path="/users", yaml={})
        state.update_tests(verb, ["test.ts"])
        state_manager.load_state()

        state_manager.config.override = True
        with patch.object(state_manager.logger, "info") as mock_info:
            result = state_manager.should_generate_tests_verb(verb)
            assert result is True
            assert mock_info.called


class TestFrameworkStateManagerUpdateModelsState:
    """Test update_models_state() method."""

    def test_update_models_state_new_path(self, state_manager, tmp_path, sample_models):
        """Test updating state with new models."""
        state_manager.update_models_state(path="/users", models=sample_models)

        # Verify state file created
        state_file = tmp_path / FrameworkState.STATE_FILENAME
        assert state_file.exists()

        # Verify state content
        loaded_state = FrameworkState.load(tmp_path)
        assert "/users" in loaded_state.generated_endpoints
        endpoint = loaded_state.get_endpoint("/users")
        assert len(endpoint.models) == 2

    def test_update_models_state_existing_path(self, state_manager, tmp_path, sample_models):
        """Test updating state with existing path (replaces models)."""
        # Create initial state
        state = FrameworkState(framework_root=tmp_path)
        initial_models = [GeneratedModel(path="old.ts", fileContent="old", summary="Old")]
        state.update_models(path="/users", models=initial_models)
        state_manager.load_state()

        # Update with new models
        state_manager.update_models_state(path="/users", models=sample_models)

        # Verify models replaced
        loaded_state = FrameworkState.load(tmp_path)
        endpoint = loaded_state.get_endpoint("/users")
        assert len(endpoint.models) == 2
        assert endpoint.models[0].path == sample_models[0].path

    def test_update_models_state_saves_file(self, state_manager, tmp_path, sample_models):
        """Test state file is saved after update."""
        state_file = tmp_path / FrameworkState.STATE_FILENAME
        assert not state_file.exists()

        state_manager.update_models_state(path="/users", models=sample_models)

        assert state_file.exists()

    def test_update_models_state_empty_models(self, state_manager, tmp_path):
        """Test with empty models list."""
        state_manager.update_models_state(path="/users", models=[])

        loaded_state = FrameworkState.load(tmp_path)
        endpoint = loaded_state.get_endpoint("/users")
        assert endpoint is not None
        assert len(endpoint.models) == 0


class TestFrameworkStateManagerUpdateTestsState:
    """Test update_tests_state() method."""

    def test_update_tests_state_new_verb(self, state_manager, tmp_path):
        """Test updating state with new tests."""
        verb = APIVerb(path="/users", verb="get", root_path="/users", yaml={})
        tests = ["src/tests/users.spec.ts"]

        state_manager.update_tests_state(verb, tests)

        # Verify state file created
        state_file = tmp_path / FrameworkState.STATE_FILENAME
        assert state_file.exists()

        # Verify state content
        loaded_state = FrameworkState.load(tmp_path)
        endpoint = loaded_state.get_endpoint("/users")
        assert endpoint is not None
        assert "/users - GET" in endpoint.verbs
        assert "src/tests/users.spec.ts" in endpoint.tests

    def test_update_tests_state_existing_verb(self, state_manager, tmp_path):
        """Test updating state with existing verb (adds to verbs list)."""
        # Create initial state
        state = FrameworkState(framework_root=tmp_path)
        verb1 = APIVerb(path="/users", verb="get", root_path="/users", yaml={})
        state.update_tests(verb1, ["test1.ts"])
        state_manager.load_state()

        # Add another verb
        verb2 = APIVerb(path="/users", verb="post", root_path="/users", yaml={})
        state_manager.update_tests_state(verb2, ["test2.ts"])

        # Verify both verbs present
        loaded_state = FrameworkState.load(tmp_path)
        endpoint = loaded_state.get_endpoint("/users")
        assert "/users - GET" in endpoint.verbs
        assert "/users - POST" in endpoint.verbs
        assert "test1.ts" in endpoint.tests
        assert "test2.ts" in endpoint.tests

    def test_update_tests_state_saves_file(self, state_manager, tmp_path):
        """Test state file is saved after update."""
        state_file = tmp_path / FrameworkState.STATE_FILENAME
        assert not state_file.exists()

        verb = APIVerb(path="/users", verb="get", root_path="/users", yaml={})
        state_manager.update_tests_state(verb, ["test.ts"])

        assert state_file.exists()

    def test_update_tests_state_empty_tests(self, state_manager, tmp_path):
        """Test with empty tests list."""
        verb = APIVerb(path="/users", verb="get", root_path="/users", yaml={})
        state_manager.update_tests_state(verb, [])

        loaded_state = FrameworkState.load(tmp_path)
        endpoint = loaded_state.get_endpoint("/users")
        assert endpoint is not None
        assert "/users - GET" in endpoint.verbs
        assert len(endpoint.tests) == 0
