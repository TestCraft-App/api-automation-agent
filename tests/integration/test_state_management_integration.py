"""
Integration tests for state management feature.
Tests state persistence, loading, and incremental generation scenarios.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.adapters.processors_adapter import ProcessorsAdapter
from src.configuration.config import Config, GenerationOptions, Envs
from src.configuration.data_sources import DataSource
from src.framework_generator import FrameworkGenerator
from src.models.generated_model import GeneratedModel
from src.services.command_service import CommandService
from src.services.file_service import FileService
from src.services.llm_service import LLMService
from src.utils.framework_state import FrameworkState

sys.path.insert(0, str(Path(__file__).parent.parent / "fixtures"))
from tests.fixtures.llm_responses import (  # noqa: E402
    get_mock_models_for_path,
    get_mock_first_test_for_verb,
)


@pytest.mark.integration
class TestStateManagementIntegration:
    """Integration tests for state management functionality."""

    def setup_method(self):
        """Set up test environment with temporary directory."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.api_spec_path = Path(__file__).parent.parent / "fixtures" / "sample_openapi_spec.json"

        self.config = Config(
            destination_folder=str(self.test_dir),
            env=Envs.DEV,
            api_definition=str(self.api_spec_path),
            endpoints=None,
            generate=GenerationOptions.MODELS_AND_FIRST_TEST,
            data_source=DataSource.SWAGGER,
            use_existing_framework=False,
            prefixes=["/"],
        )

    def teardown_method(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _create_mock_llm_service(self, file_service: FileService):
        """Create a mock LLM service with pre-defined responses."""
        llm_service = LLMService(self.config, file_service)

        def mock_generate_models(definition_content):
            mock_models = get_mock_models_for_path("/pets")
            for model in mock_models:
                file_path = Path(self.config.destination_folder) / model.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(model.fileContent, encoding="utf-8")
            return mock_models

        def mock_generate_first_test(verb_content, models):
            if "POST" in verb_content or "post" in verb_content:
                mock_tests = get_mock_first_test_for_verb("/pets", "post")
            elif "/{petId}" in verb_content:
                mock_tests = get_mock_first_test_for_verb("/pets/{petId}", "get")
            else:
                mock_tests = get_mock_first_test_for_verb("/pets", "get")

            for test in mock_tests:
                file_path = Path(self.config.destination_folder) / test.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(test.fileContent, encoding="utf-8")
            return mock_tests

        def mock_get_additional_models(relevant_models, other_models):
            return None

        llm_service.generate_models = Mock(side_effect=mock_generate_models)
        llm_service.generate_first_test = Mock(side_effect=mock_generate_first_test)
        llm_service.get_additional_models = Mock(side_effect=mock_get_additional_models)
        llm_service.fix_typescript = Mock(return_value=None)

        return llm_service

    def _create_mock_command_service(self):
        """Create a mock command service."""
        command_service = CommandService(self.config)
        command_service.install_dependencies = Mock(return_value=None)
        command_service.run_command_silently = Mock(return_value="")
        command_service.format_files = Mock(return_value=None)
        command_service.run_linter = Mock(return_value=None)
        command_service.get_generated_test_files = Mock(return_value=[])
        command_service.run_typescript_compiler_for_files = Mock(return_value=None)
        command_service.run_command_with_fix = Mock(side_effect=lambda f, fix, files: f(files))

        return command_service

    def test_state_file_created_after_generation(self):
        """Test state file is created after generation."""
        file_service = FileService()
        llm_service = self._create_mock_llm_service(file_service)
        command_service = self._create_mock_command_service()

        processors_adapter = ProcessorsAdapter(config=self.config, file_service=file_service)
        api_processor = processors_adapter.swagger_processor()

        generator = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        api_definition = generator.process_api_definition()
        generator.setup_framework(api_definition)
        generator.create_env_file(api_definition)
        generator.generate(api_definition, GenerationOptions.MODELS)

        state_file = Path(self.config.destination_folder) / "framework-state.json"
        assert state_file.exists()

    def test_state_file_contains_correct_structure(self):
        """Test state file contains correct structure."""
        file_service = FileService()
        llm_service = self._create_mock_llm_service(file_service)
        command_service = self._create_mock_command_service()

        processors_adapter = ProcessorsAdapter(config=self.config, file_service=file_service)
        api_processor = processors_adapter.swagger_processor()

        generator = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        api_definition = generator.process_api_definition()
        generator.setup_framework(api_definition)
        generator.create_env_file(api_definition)
        generator.generate(api_definition, GenerationOptions.MODELS)

        # Verify state file structure
        state_file = Path(self.config.destination_folder) / "framework-state.json"
        state_data = json.loads(state_file.read_text(encoding="utf-8"))

        assert "generated_endpoints" in state_data
        assert isinstance(state_data["generated_endpoints"], list)
        assert len(state_data["generated_endpoints"]) > 0

        # Verify endpoint structure
        endpoint = state_data["generated_endpoints"][0]
        assert "path" in endpoint
        assert "models" in endpoint
        assert "verbs" in endpoint
        assert "tests" in endpoint

    def test_state_persists_across_runs(self):
        """Test state persists across multiple runs."""
        file_service = FileService()
        llm_service = self._create_mock_llm_service(file_service)
        command_service = self._create_mock_command_service()

        processors_adapter = ProcessorsAdapter(config=self.config, file_service=file_service)
        api_processor = processors_adapter.swagger_processor()

        generator1 = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        api_definition1 = generator1.process_api_definition()
        generator1.setup_framework(api_definition1)
        generator1.create_env_file(api_definition1)
        generator1.generate(api_definition1, GenerationOptions.MODELS)

        state_file = Path(self.config.destination_folder) / "framework-state.json"
        assert state_file.exists()

        self.config.use_existing_framework = True
        generator2 = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        generator2.state_manager.load_state()

        assert generator2.state_manager.get_endpoint_count() > 0

    def test_preloaded_models_available_in_subsequent_runs(self):
        """Test preloaded models are available in subsequent runs."""
        file_service = FileService()
        llm_service = self._create_mock_llm_service(file_service)
        command_service = self._create_mock_command_service()

        processors_adapter = ProcessorsAdapter(config=self.config, file_service=file_service)
        api_processor = processors_adapter.swagger_processor()

        generator1 = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        api_definition1 = generator1.process_api_definition()
        generator1.setup_framework(api_definition1)
        generator1.create_env_file(api_definition1)
        generator1.generate(api_definition1, GenerationOptions.MODELS)

        self.config.use_existing_framework = True
        generator2 = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        generator2.state_manager.load_state()
        preloaded_models = generator2.state_manager.get_preloaded_model_info()

        assert len(preloaded_models) > 0
        assert preloaded_models[0].path == "/pets"
        assert len(preloaded_models[0].models) > 0

    def test_skip_mode_preserves_existing_endpoints(self, monkeypatch):
        """Test skip mode preserves existing endpoints."""
        file_service = FileService()
        llm_service = self._create_mock_llm_service(file_service)
        command_service = self._create_mock_command_service()

        processors_adapter = ProcessorsAdapter(config=self.config, file_service=file_service)
        api_processor = processors_adapter.swagger_processor()

        generator1 = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        api_definition1 = generator1.process_api_definition()
        generator1.setup_framework(api_definition1)
        generator1.create_env_file(api_definition1)
        generator1.generate(api_definition1, GenerationOptions.MODELS)

        models_dir = Path(self.config.destination_folder) / "src" / "models"
        initial_model_files = list(models_dir.rglob("*.ts"))

        self.config.use_existing_framework = True
        self.config.override = False

        generator2 = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        generator2.state_manager.load_state()
        api_definition2 = generator2.process_api_definition()

        def mock_input(prompt):
            return "2"

        monkeypatch.setattr("builtins.input", mock_input)

        llm_service.generate_models.reset_mock()

        generator2.generate(api_definition2, GenerationOptions.MODELS)

        assert not llm_service.generate_models.called

        final_model_files = list(models_dir.rglob("*.ts"))
        assert len(final_model_files) == len(initial_model_files)

    def test_incremental_generation_adds_new_endpoints(self):
        """Test generating new endpoints adds to state."""
        file_service = FileService()
        llm_service = self._create_mock_llm_service(file_service)
        command_service = self._create_mock_command_service()

        processors_adapter = ProcessorsAdapter(config=self.config, file_service=file_service)
        api_processor = processors_adapter.swagger_processor()

        self.config.endpoints = ["/pets"]
        generator1 = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        api_definition1 = generator1.process_api_definition()
        generator1.setup_framework(api_definition1)
        generator1.create_env_file(api_definition1)
        generator1.generate(api_definition1, GenerationOptions.MODELS)

        state_file = Path(self.config.destination_folder) / "framework-state.json"
        initial_state = json.loads(state_file.read_text(encoding="utf-8"))
        initial_count = len(initial_state["generated_endpoints"])

        self.config.endpoints = None
        self.config.use_existing_framework = True
        generator2 = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        generator2.state_manager.load_state()
        api_definition2 = generator2.process_api_definition()
        generator2.generate(api_definition2, GenerationOptions.MODELS)

        final_state = json.loads(state_file.read_text(encoding="utf-8"))
        final_count = len(final_state["generated_endpoints"])

        assert final_count >= initial_count

    def test_test_state_tracked_correctly(self):
        """Test test state is tracked correctly."""
        file_service = FileService()
        llm_service = self._create_mock_llm_service(file_service)
        command_service = self._create_mock_command_service()

        processors_adapter = ProcessorsAdapter(config=self.config, file_service=file_service)
        api_processor = processors_adapter.swagger_processor()

        generator = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        api_definition = generator.process_api_definition()
        generator.setup_framework(api_definition)
        generator.create_env_file(api_definition)
        generator.generate(api_definition, GenerationOptions.MODELS_AND_FIRST_TEST)

        # Verify test state in framework state
        state_file = Path(self.config.destination_folder) / "framework-state.json"
        state_data = json.loads(state_file.read_text(encoding="utf-8"))

        # Find endpoint with tests
        endpoint_with_tests = None
        for endpoint in state_data["generated_endpoints"]:
            if endpoint.get("tests") or endpoint.get("verbs"):
                endpoint_with_tests = endpoint
                break

        if endpoint_with_tests:
            assert "verbs" in endpoint_with_tests
            assert "tests" in endpoint_with_tests

    def test_corrupted_state_file_handled_gracefully(self):
        """Test corrupted state file is handled gracefully."""
        # Create corrupted state file
        state_file = Path(self.config.destination_folder) / "framework-state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("{invalid json", encoding="utf-8")

        file_service = FileService()
        llm_service = self._create_mock_llm_service(file_service)
        command_service = self._create_mock_command_service()

        processors_adapter = ProcessorsAdapter(config=self.config, file_service=file_service)
        api_processor = processors_adapter.swagger_processor()

        generator = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        generator.state_manager.load_state()

        assert generator.state_manager.get_endpoint_count() == 0

    def test_missing_state_file_creates_new_state(self):
        """Test missing state file creates new state."""
        file_service = FileService()
        llm_service = self._create_mock_llm_service(file_service)
        command_service = self._create_mock_command_service()

        processors_adapter = ProcessorsAdapter(config=self.config, file_service=file_service)
        api_processor = processors_adapter.swagger_processor()

        generator = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        generator.state_manager.load_state()
        assert generator.state_manager.get_endpoint_count() == 0

        api_definition = generator.process_api_definition()
        generator.setup_framework(api_definition)
        generator.create_env_file(api_definition)
        generator.generate(api_definition, GenerationOptions.MODELS)

        state_file = Path(self.config.destination_folder) / "framework-state.json"
        assert state_file.exists()

    def test_missing_model_files_handled_gracefully(self):
        """Test missing model files don't break generation."""
        # Create state file with models, but don't create the actual model files
        state = FrameworkState()
        models = [GeneratedModel(path="src/models/missing.ts", fileContent="content", summary="Missing")]
        state.update_models(path="/users", models=models)
        state.save(Path(self.config.destination_folder))

        file_service = FileService()
        llm_service = self._create_mock_llm_service(file_service)
        command_service = self._create_mock_command_service()

        processors_adapter = ProcessorsAdapter(config=self.config, file_service=file_service)
        api_processor = processors_adapter.swagger_processor()

        generator = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        # Should not raise exception
        generator.state_manager.load_state()

        preloaded = generator.state_manager.get_preloaded_model_info()
        assert len(preloaded) == 0
