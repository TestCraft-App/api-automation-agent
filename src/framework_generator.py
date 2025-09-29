import signal
import sys
import traceback
from typing import List, Dict, Optional, cast

from .ai_tools.models.file_spec import FileSpec
from .configuration.config import Config, GenerationOptions
from .configuration.data_sources import DataSource
from .models import APIDefinition, APIPath, APIVerb, ModelInfo, GeneratedModel
from .models.usage_data import AggregatedUsageMetadata
from .processors.api_processor import APIProcessor
from .processors.postman_processor import PostmanProcessor
from .services.command_service import CommandService
from .services.file_service import FileService
from .services.llm_service import LLMService
from .utils.checkpoint import Checkpoint
from .utils.logger import Logger


class FrameworkGenerator:
    def __init__(
        self,
        config: Config,
        llm_service: LLMService,
        command_service: CommandService,
        file_service: FileService,
        api_processor: APIProcessor,
    ):
        self.config = config
        self.llm_service = llm_service
        self.command_service = command_service
        self.file_service = file_service
        self.api_processor = api_processor
        self.models_count = 0
        self.test_files_count = 0
        self.logger = Logger.get_logger(__name__)
        self.checkpoint = Checkpoint(self, "framework_generator", self.config.destination_folder)

        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, _signum, _frame):
        self.logger.warning("⚠️ Process interrupted! Saving progress...")
        try:
            self.save_state()
        except Exception as e:
            self.logger.error(f"Error while saving state: {e}")
        sys.exit(1)

    def _log_error(self, message: str, exc: Exception):
        self.logger.error(f"{message}: {exc}")

    def save_state(self):
        self.checkpoint.save(
            state={
                "destination_folder": self.config.destination_folder,
                "self": {"models_count": self.models_count, "test_files_count": self.test_files_count},
            }
        )

    def restore_state(self, namespace: str):
        self.checkpoint.namespace = namespace
        self.checkpoint.restore(restore_object=True)

    def get_aggregated_usage_metadata(self) -> AggregatedUsageMetadata:
        return self.llm_service.get_aggregated_usage_metadata()

    @Checkpoint.checkpoint()
    def process_api_definition(
        self, api_definitions_list: Optional[List[APIDefinition]] = None
    ) -> APIDefinition:
        """
        Process one or more API definitions and merge them into a single APIDefinition.
        Uses `APIDefinition.from_dict()` to ensure object consistency.
        """
        try:
            api_definitions: List[APIDefinition] = []

            if api_definitions_list:
                for api_def in api_definitions_list:
                    api_def.endpoints = self.config.endpoints
                    api_definitions.append(api_def)
            else:
                for api_file in self.config.api_definitions:
                    self.logger.info(f"\nProcessing API definition from {api_file}")
                    api_def = self.api_processor.process_api_definition(api_file)
                    api_def.endpoints = self.config.endpoints
                    api_definitions.append(api_def)

            if not api_definitions:
                raise ValueError("No API definitions processed. Provide at least one OpenAPI file.")

            # Merge all API definitions
            merged_api = api_definitions[0]
            for other_def in api_definitions[1:]:
                if hasattr(other_def, "definitions") and hasattr(merged_api, "definitions"):
                    merged_api.definitions.extend(
                        [d for d in other_def.definitions if d not in merged_api.definitions]
                    )

            return merged_api

        except Exception as e:
            self._log_error("Error processing API definitions", e)
            raise

    @Checkpoint.checkpoint()
    def setup_framework(self, api_definition: APIDefinition):
        try:
            self.logger.info(f"\nSetting up framework in {self.config.destination_folder}")
            self.file_service.copy_framework_template(self.config.destination_folder)

            if self.config.data_source == DataSource.POSTMAN:
                cast(PostmanProcessor, self.api_processor).update_framework_for_postman(
                    self.config.destination_folder, api_definition
                )

            self.command_service.install_dependencies()
        except Exception as e:
            self._log_error("Error setting up framework", e)
            raise

    @Checkpoint.checkpoint()
    def create_env_file(self, api_definition: APIDefinition):
        try:
            self.api_processor.create_dot_env(api_definition)
        except Exception as e:
            self._log_error("Error creating .env file", e)
            raise

    @Checkpoint.checkpoint()
    def generate(self, api_definition: APIDefinition, generate_tests: GenerationOptions):
        try:
            self.logger.info("\nProcessing API definitions")
            all_generated_models = {"info": []}

            api_paths = self.api_processor.get_api_paths(api_definition)
            api_verbs = self.api_processor.get_api_verbs(api_definition)

            for path in self.checkpoint.checkpoint_iter(api_paths, "generate_paths", all_generated_models):
                models = self._generate_models(path)
                if models:
                    model_info = ModelInfo(
                        path=self.api_processor.get_api_path_name(path),
                        files=[model.path + " - " + model.summary for model in models],
                        models=models,
                    )
                    all_generated_models["info"].append(model_info)
                    self.logger.debug(f"Generated models for path: {self.api_processor.get_api_path_name(path)}")

            if generate_tests in (GenerationOptions.MODELS_AND_FIRST_TEST, GenerationOptions.MODELS_AND_TESTS):
                for verb in self.checkpoint.checkpoint_iter(api_verbs, "generate_verbs"):
                    service_related_to_verb = self.api_processor.get_api_verb_rootpath(verb)
                    tests = self._generate_tests(verb, all_generated_models["info"], generate_tests)
                    if not tests:
                        tests = []
                    for file in filter(self._is_response_file, tests):
                        for model in all_generated_models["info"]:
                            if model.path == service_related_to_verb:
                                model.files.append(file.path)
                                model.models.append(GeneratedModel(path=file.path, fileContent=file.fileContent, summary=""))

                    self.logger.debug(
                        f"Generated tests for path: {self.api_processor.get_api_verb_path(verb)} - "
                        f"{self.api_processor.get_api_verb_name(verb)}"
                    )

            self.logger.info(f"\nGeneration complete. {self.models_count} models and {self.test_files_count} tests were generated.")
        except Exception as e:
            self._log_error("Error processing definitions", e)
            self.save_state()
            raise

    @Checkpoint.checkpoint()
    def run_final_checks(self, generate_tests: GenerationOptions) -> Optional[List[Dict[str, str]]]:
        try:
            if generate_tests in (GenerationOptions.MODELS_AND_FIRST_TEST, GenerationOptions.MODELS_AND_TESTS):
                test_files = self.command_service.get_generated_test_files()
                if test_files:
                    return test_files
                self.logger.warning("⚠️ No test files found! Skipping tests.")
            return None
        except Exception as e:
            self._log_error("Error during final checks", e)
            raise

    def _generate_models(self, api_definition: APIPath | str) -> Optional[List[GeneratedModel]]:
        try:
            path_name = self.api_processor.get_api_path_name(api_definition)
            self.logger.info(f"Generating models for {path_name}")
            definition_content = self.api_processor.get_api_path_content(api_definition)
            models_result = self.llm_service.generate_models(definition_content)
            if not models_result:
                self.logger.warning(f"No models generated for {path_name}")
                return None

            self.models_count += len(models_result)
            self._run_code_quality_checks(models_result, are_models=True)
            return GeneratedModel.from_model_file_specs(models_result)
        except Exception as e:
            self._log_error(f"Error generating models for {path_name}", e)
            return None

    def _generate_tests(self, api_verb: APIVerb, all_models: List[ModelInfo], generate_tests: GenerationOptions) -> Optional[List[FileSpec]]:
        verb_path = self.api_processor.get_api_verb_path(api_verb)
        verb_name = self.api_processor.get_api_verb_name(api_verb)
        try:
            relevant_models = self.api_processor.get_relevant_models(all_models, api_verb)
            other_models = self.api_processor.get_other_models(all_models, api_verb)

            if other_models:
                additional_models = self.llm_service.get_additional_models(relevant_models, other_models)
                if additional_models:
                    for model in additional_models:
                        generated_model = GeneratedModel(path=model.path, fileContent=model.fileContent)
                        relevant_models.append(generated_model)

            tests_result = self.llm_service.generate_first_test(
                self.api_processor.get_api_verb_content(api_verb),
                relevant_models,
            )

            if tests_result:
                self.test_files_count += len(tests_result)
                self.save_state()
                self._run_code_quality_checks(tests_result)
                if generate_tests == GenerationOptions.MODELS_AND_TESTS:
                    return self._generate_additional_tests(tests_result, relevant_models, api_verb)
            return tests_result
        except Exception as e:
            self._log_error(f"Error generating tests for {verb_path} - {verb_name}", e)
            raise

    def _generate_additional_tests(self, tests: List[FileSpec], models: List[GeneratedModel | str], api_definition: APIVerb) -> Optional[List[FileSpec]]:
        verb_path = self.api_processor.get_api_verb_path(api_definition)
        verb_name = self.api_processor.get_api_verb_name(api_definition)
        try:
            additional_tests = self.llm_service.generate_additional_tests(tests, models, self.api_processor.get_api_verb_content(api_definition))
            if additional_tests and len(additional_tests) > len(tests):
                self.test_files_count += len(additional_tests) - len(tests)
                self.save_state()
                self._run_code_quality_checks(additional_tests)
                return additional_tests
            return tests
        except Exception as e:
            self._log_error(f"Error generating additional tests for {verb_path} - {verb_name}\n{traceback.format_exc()}", e)
            return tests

    def _run_code_quality_checks(self, files: List[FileSpec], are_models: bool = False):
        error_type = "models" if are_models else "tests"
        try:
            def typescript_fix_wrapper(problematic_files: List[FileSpec], messages):
                self.logger.info("\nAttempting to fix TypeScript errors with LLM...")
                self.llm_service.fix_typescript(problematic_files, messages, are_models)
                self.logger.info("TypeScript fixing complete.")

            self.command_service.run_command_with_fix(
                self.command_service.run_typescript_compiler_for_files,
                typescript_fix_wrapper,
                files,
            )
            self.command_service.format_files()
            self.command_service.run_linter()
        except Exception as e:
            self._log_error(f"Error during code quality checks for {error_type}", e)

    @staticmethod
    def _is_response_file(file: FileSpec) -> bool:
        return GeneratedModel.is_response_file(file.path)
