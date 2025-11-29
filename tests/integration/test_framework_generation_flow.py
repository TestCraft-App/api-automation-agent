"""
Integration tests for end-to-end framework generation flow.
Tests the complete workflow from API definition processing through model and test generation.
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
from src.services.command_service import CommandService
from src.services.file_service import FileService
from src.services.llm_service import LLMService
from src.utils.checkpoint import Checkpoint

sys.path.insert(0, str(Path(__file__).parent.parent / "fixtures"))
from tests.fixtures.llm_responses import (  # noqa: E402
    get_mock_models_for_path,
    get_mock_first_test_for_verb,
    get_mock_additional_tests,
)


@pytest.mark.integration
class TestFrameworkGenerationFlow:
    """Integration tests for the complete framework generation workflow."""

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

        def mock_generate_additional_tests(tests, models, verb_content):
            mock_tests = get_mock_additional_tests()
            for test in mock_tests:
                file_path = Path(self.config.destination_folder) / test.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(test.fileContent, encoding="utf-8")
            return mock_tests

        def mock_get_additional_models(relevant_models, other_models):
            return None

        llm_service.generate_models = Mock(side_effect=mock_generate_models)
        llm_service.generate_first_test = Mock(side_effect=mock_generate_first_test)
        llm_service.generate_additional_tests = Mock(side_effect=mock_generate_additional_tests)
        llm_service.get_additional_models = Mock(side_effect=mock_get_additional_models)
        llm_service.fix_typescript = Mock(return_value=None)

        return llm_service

    def _create_mock_command_service(self):
        """Create a mock command service that simulates successful operations."""
        command_service = CommandService(self.config)

        command_service.install_dependencies = Mock(return_value=None)

        def mock_run_command_silently(command, cwd=None, env_vars=None):
            if "tsc" in command and "--noEmit" in command:
                return ""
            elif "prettier" in command:
                return ""
            elif "eslint" in command:
                return ""
            return ""

        command_service.run_command_silently = Mock(side_effect=mock_run_command_silently)

        command_service.format_files = Mock(return_value=None)
        command_service.run_linter = Mock(return_value=None)

        def mock_get_generated_test_files():
            test_files = []
            tests_dir = Path(self.config.destination_folder) / "src" / "tests"
            if tests_dir.exists():
                for test_file in tests_dir.rglob("*.spec.ts"):
                    test_files.append({"path": str(test_file)})
            return test_files

        command_service.get_generated_test_files = Mock(side_effect=mock_get_generated_test_files)

        command_service.run_typescript_compiler_for_files = Mock(return_value=None)

        def mock_run_command_with_fix(command_func, fix_func, files):
            try:
                command_func(files)
            except Exception:
                pass

        command_service.run_command_with_fix = Mock(side_effect=mock_run_command_with_fix)

        return command_service

    def test_end_to_end_framework_generation_models_only(self):
        """Test complete framework generation flow with models only."""
        self.config.generate = GenerationOptions.MODELS

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
        assert api_definition is not None
        assert len(api_definition.definitions) > 0

        generator.setup_framework(api_definition)
        assert Path(self.config.destination_folder).exists()
        assert (Path(self.config.destination_folder) / "package.json").exists()
        assert (Path(self.config.destination_folder) / "tsconfig.json").exists()

        generator.create_env_file(api_definition)
        assert (Path(self.config.destination_folder) / ".env").exists()

        generator.generate(api_definition, GenerationOptions.MODELS)

        models_dir = Path(self.config.destination_folder) / "src" / "models"
        assert models_dir.exists()

        assert llm_service.generate_models.called
        assert generator.models_count > 0

    def test_end_to_end_framework_generation_with_first_test(self):
        """Test complete framework generation flow with models and first test."""
        self.config.generate = GenerationOptions.MODELS_AND_FIRST_TEST

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

        models_dir = Path(self.config.destination_folder) / "src" / "models"
        assert models_dir.exists()

        tests_dir = Path(self.config.destination_folder) / "src" / "tests"
        assert tests_dir.exists()

        assert llm_service.generate_models.called
        assert llm_service.generate_first_test.called
        assert generator.models_count > 0
        assert generator.test_files_count > 0

    def test_end_to_end_framework_generation_with_all_tests(self):
        """Test complete framework generation flow with models and all tests."""
        self.config.generate = GenerationOptions.MODELS_AND_TESTS

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
        generator.generate(api_definition, GenerationOptions.MODELS_AND_TESTS)

        models_dir = Path(self.config.destination_folder) / "src" / "models"
        tests_dir = Path(self.config.destination_folder) / "src" / "tests"

        assert models_dir.exists()
        assert tests_dir.exists()

        assert llm_service.generate_models.called
        assert llm_service.generate_first_test.called
        assert llm_service.generate_additional_tests.called

        assert generator.models_count > 0
        assert generator.test_files_count > 0

    def test_framework_generation_with_specific_endpoints(self):
        """Test framework generation with specific endpoints filter."""
        self.config.endpoints = ["/pets"]
        self.config.generate = GenerationOptions.MODELS_AND_FIRST_TEST

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

        paths_in_definition = [d.path for d in api_definition.definitions]
        assert all("/pets" in path for path in paths_in_definition)

        generator.setup_framework(api_definition)
        generator.create_env_file(api_definition)
        generator.generate(api_definition, GenerationOptions.MODELS_AND_FIRST_TEST)

        assert generator.models_count > 0
        assert generator.test_files_count > 0

    def test_framework_generation_run_final_checks(self):
        """Test framework generation with final checks including test file discovery."""
        self.config.generate = GenerationOptions.MODELS_AND_FIRST_TEST

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

        generator.run_final_checks(GenerationOptions.MODELS_AND_FIRST_TEST)

        assert command_service.get_generated_test_files.called

    def test_framework_generation_handles_api_processor_correctly(self):
        """Test that framework generation correctly uses the API processor."""
        self.config.generate = GenerationOptions.MODELS

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

        assert api_definition is not None
        assert hasattr(api_definition, "definitions")
        assert hasattr(api_definition, "base_yaml")
        assert len(api_definition.definitions) > 0

        paths = [d.path for d in api_definition.definitions]
        assert any("/pets" in path for path in paths)

    def test_framework_generation_with_existing_framework(self):
        """Test framework generation using an existing framework."""
        self.config.generate = GenerationOptions.MODELS
        self.config.use_existing_framework = False

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

        models_dir = Path(self.config.destination_folder) / "src" / "models"
        initial_model_count = len(list(models_dir.rglob("*.ts")))

        self.config.use_existing_framework = True

        generator2 = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service,
            command_service=command_service,
            file_service=file_service,
            api_processor=api_processor,
        )

        api_definition2 = generator2.process_api_definition()
        generator2.generate(api_definition2, GenerationOptions.MODELS)

        models_dir = Path(self.config.destination_folder) / "src" / "models"
        assert models_dir.exists()
        final_model_count = len(list(models_dir.rglob("*.ts")))
        assert final_model_count > 0
        assert (
            final_model_count >= initial_model_count
        ), f"Model count should grow or stay same: {initial_model_count} -> {final_model_count}"

    def test_framework_generation_aggregates_usage_metadata(self):
        """Test that framework generation aggregates LLM usage metadata."""
        self.config.generate = GenerationOptions.MODELS

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

        usage_metadata = generator.get_aggregated_usage_metadata()

        assert usage_metadata is not None
        assert hasattr(usage_metadata, "total_input_tokens")
        assert hasattr(usage_metadata, "total_output_tokens")
        assert hasattr(usage_metadata, "total_cost")

    def test_framework_state_saved_and_loaded_between_runs(self):
        """Ensure framework-state.json captures metadata and can be reloaded."""
        self.config.generate = GenerationOptions.MODELS_AND_FIRST_TEST

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
        generator.generate(api_definition, self.config.generate)

        state_file = Path(self.config.destination_folder) / "framework-state.json"
        assert state_file.exists()

        state_payload = json.loads(state_file.read_text(encoding="utf-8"))
        assert state_payload.get("generated_endpoints")

        self.config.use_existing_framework = True
        file_service2 = FileService()
        llm_service2 = self._create_mock_llm_service(file_service2)
        command_service2 = self._create_mock_command_service()

        processors_adapter2 = ProcessorsAdapter(config=self.config, file_service=file_service2)
        api_processor2 = processors_adapter2.swagger_processor()

        generator2 = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service2,
            command_service=command_service2,
            file_service=file_service2,
            api_processor=api_processor2,
        )
        generator2.state_manager.load_state()
        preloaded_models = generator2.state_manager.get_preloaded_model_info()

        assert preloaded_models, "Existing models should be loaded from state."
        first_endpoint = preloaded_models[0].path
        assert first_endpoint == "/pets"
        assert generator2.state_manager.get_endpoint_state(first_endpoint) is not None

    def test_existing_framework_respects_override_prompt(self, monkeypatch):
        """Verify that an existing endpoint is skipped when user declines override."""
        self.config.generate = GenerationOptions.MODELS

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
        generator.generate(api_definition, self.config.generate)

        # Clear checkpoints to allow second generator to run
        Checkpoint.clear()

        self.config.use_existing_framework = True
        self.config.force = False

        file_service2 = FileService()
        llm_service2 = self._create_mock_llm_service(file_service2)
        command_service2 = self._create_mock_command_service()

        processors_adapter2 = ProcessorsAdapter(config=self.config, file_service=file_service2)
        api_processor2 = processors_adapter2.swagger_processor()

        generator2 = FrameworkGenerator(
            config=self.config,
            llm_service=llm_service2,
            command_service=command_service2,
            file_service=file_service2,
            api_processor=api_processor2,
        )
        generator2.state_manager.load_state()
        api_definition2 = generator2.process_api_definition()

        prompt_calls = {"count": 0}

        def mock_input(_):
            prompt_calls["count"] += 1
            return "2"  # Choose option 2: Skip existing files

        monkeypatch.setattr("builtins.input", mock_input)
        llm_service2.generate_models.reset_mock()

        generator2.generate(api_definition2, self.config.generate)

        assert prompt_calls["count"] >= 1
        assert not llm_service2.generate_models.called
