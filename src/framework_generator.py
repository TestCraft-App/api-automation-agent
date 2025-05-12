import signal
import sys
from typing import List, Dict, Any, Optional, cast

from src.configuration.data_sources import DataSource
from src.processors.api_processor import APIProcessor
from src.ai_tools.models.file_spec import FileSpec
from src.configuration.config import Config, GenerationOptions
from src.processors.postman_processor import PostmanProcessor
from src.services.command_service import CommandService
from src.services.file_service import FileService
from src.services.llm_service import LLMService
from src.utils.checkpoint import Checkpoint
from src.utils.logger import Logger
from src.models import APIPath, APIVerb, GeneratedModel, GeneratedModels, ModelInfo, APIDefinition


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
            self.logger.error(f"Error saving state: {e}")
        sys.exit(1)

    def _log_error(self, message: str, exc: Exception):
        """Helper method to log errors consistently"""
        self.logger.error(f"{message}: {exc}")

    def save_state(self):
        self.checkpoint.save(
            state={
                "destination_folder": self.config.destination_folder,
                "self": {
                    "models_count": self.models_count,
                    "test_files_count": self.test_files_count,
                },
            }
        )

    def restore_state(self, namespace: str):
        self.checkpoint.namespace = namespace
        self.checkpoint.restore(restore_object=True)

    @Checkpoint.checkpoint()
    def process_api_definition(self) -> APIDefinition:
        """Process the API definition file and return a list of API endpoints"""
        try:
            self.logger.info(f"\nProcessing API definition from {self.config.api_definition}")
            api_definition = self.api_processor.process_api_definition(self.config.api_definition)
            api_definition.endpoints = self.config.endpoints
            return api_definition
        except Exception as e:
            self._log_error("Error processing API definition", e)
            raise

    @Checkpoint.checkpoint()
    def setup_framework(self, api_definition: APIDefinition):
        """Set up the framework environment"""
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
        """Generate the .env file from the provided API definition"""
        try:
            self.logger.info("\nGenerating .env file")
            env_vars_data = self.api_processor.extract_env_vars(api_definition)
            self.llm_service.generate_dot_env(env_vars_data)
        except Exception as e:
            self._log_error("Error creating .env file", e)
            raise

    @Checkpoint.checkpoint()
    def generate(
        self,
        api_definition: APIDefinition,
        generate_tests: GenerationOptions,
    ):
        """Process the API definitions and generate models and tests"""
        try:
            self.logger.info("\nProcessing API definitions")
            all_generated_models = GeneratedModels()

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
                    all_generated_models.info.append(model_info)
                    self.logger.debug(
                        "Generated models for path: " + self.api_processor.get_api_path_name(path)
                    )

            if generate_tests in (
                GenerationOptions.MODELS_AND_FIRST_TEST,
                GenerationOptions.MODELS_AND_TESTS,
            ):
                for verb in self.checkpoint.checkpoint_iter(api_verbs, "generate_verbs"):
                    service_related_to_verb = self.api_processor.get_api_verb_rootpath(verb)
                    tests = self._generate_tests(verb, all_generated_models.info, generate_tests)
                    if tests:
                        for file in filter(self._is_response_file, tests):
                            for model in all_generated_models.info:
                                if model.path == service_related_to_verb:
                                    model.files.append(file.path)
                                    model.models.append(
                                        GeneratedModel(
                                            path=file.path, fileContent=file.fileContent, summary=""
                                        )
                                    )

                        self.logger.debug(
                            f"Generated tests for path: {self.api_processor.get_api_verb_path(verb)} - {self.api_processor.get_api_verb_name(verb)}"
                        )
            self.logger.info(
                f"\nGeneration complete. "
                f"{self.models_count} models and {self.test_files_count} tests were generated."
            )
        except Exception as e:
            self._log_error("Error processing definitions", e)
            self.save_state()
            raise

    @Checkpoint.checkpoint()
    def run_final_checks(self, generate_tests: GenerationOptions) -> Optional[List[Dict[str, str]]]:
        """Run final checks like TypeScript compilation"""
        try:
            if generate_tests in (
                GenerationOptions.MODELS_AND_FIRST_TEST,
                GenerationOptions.MODELS_AND_TESTS,
            ):
                test_files = self.command_service.get_generated_test_files()
                if test_files:
                    return test_files
                self.logger.warning("⚠️ No test files found! Skipping tests.")

            return None
        except Exception as e:
            self._log_error("Error during final checks", e)
            raise

    def _generate_models(self, api_definition: APIPath) -> Optional[List[GeneratedModel]]:
        """Generate models for the API definition."""
        try:
            self.logger.info(f"Generating models for {api_definition.path}")
            model_info = ModelInfo(path=api_definition.path)

            # Generate models using LLM service
            generated_models = self.llm_service.generate_models(api_definition)
            if not generated_models:
                self.logger.warning(f"No models generated for {api_definition.path}")
                return None

            # Add each generated model to the model info
            for model in generated_models:
                model_info.add_model(model)

            self.logger.info(f"Generated {len(generated_models)} models for {api_definition.path}")
            return model_info.models

        except Exception as e:
            self.logger.error(f"Error generating models: {str(e)}")
            return None

    def _generate_tests(
        self,
        api_verb: APIVerb,
        all_models: List[ModelInfo],
        generate_tests: GenerationOptions,
    ) -> Optional[List[FileSpec]]:
        """Generate tests for a specific verb (HTTP method) in the API definition"""
        try:
            relevant_models = self.api_processor.get_relevant_models(all_models, api_verb)
            other_models = self.api_processor.get_other_models(all_models, api_verb)
            self.logger.info(
                f"\nGenerating first test for path: {self.api_processor.get_api_verb_path(api_verb)} and verb: {self.api_processor.get_api_verb_name(api_verb)}"
            )

            if other_models:
                additional_models: List[FileSpec] = self.llm_service.get_additional_models(
                    relevant_models,
                    other_models,
                )
                self.logger.info(f"\nAdding additional models: {[model.path for model in additional_models]}")
                relevant_models.extend(map(lambda x: GeneratedModel(**x.to_json()), additional_models))

            tests = self.llm_service.generate_first_test(
                self.api_processor.get_api_verb_content(api_verb),
                relevant_models,
            )

            if tests:
                self.test_files_count += len(tests)
                self.save_state()

                self._run_code_quality_checks(tests)
                if generate_tests == GenerationOptions.MODELS_AND_TESTS:
                    additional_tests = self._generate_additional_tests(
                        tests,
                        relevant_models,
                        api_verb,
                    )

                    return additional_tests

                return tests

            else:
                self.logger.warning(
                    f"No tests generated for {self.api_processor.get_api_verb_path(api_verb)} - {self.api_processor.get_api_verb_name(api_verb)}"
                )
                return None
        except Exception as e:
            self._log_error(
                f"Error processing verb definition for {self.api_processor.get_api_verb_path(api_verb)} - {self.api_processor.get_api_verb_name(api_verb)}",
                e,
            )
            raise

    def _generate_additional_tests(
        self,
        tests: List[FileSpec],
        models: List[GeneratedModel],
        api_definition: APIVerb,
    ):
        """Generate additional tests based on the initial test and models"""
        try:
            self.logger.info(
                f"\nGenerating additional tests for path: {self.api_processor.get_api_verb_path(api_definition)} and verb: {self.api_processor.get_api_verb_name(api_definition)}"
            )

            additional_tests = self.llm_service.generate_additional_tests(
                tests,
                models,
                self.api_processor.get_api_path_content(api_definition),
            )
            if additional_tests:
                self.save_state()
                self._run_code_quality_checks(additional_tests)

            return additional_tests
        except Exception as e:
            self._log_error(
                f"Error generating additional tests for {self.api_processor.get_api_verb_path(api_definition)} - {self.api_processor.get_api_verb_name(api_definition)}",
                e,
            )
            raise

    def _run_code_quality_checks(self, files: List[GeneratedModel], are_models: bool = False):
        """Run code quality checks including TypeScript compilation, linting, and formatting"""
        try:

            def typescript_fix_wrapper(problematic_files, messages):
                self.llm_service.fix_typescript(problematic_files, messages, are_models)

            self.command_service.run_command_with_fix(
                self.command_service.run_typescript_compiler_for_files,
                typescript_fix_wrapper,
                files,
            )
            self.command_service.format_files()
            self.command_service.run_linter()
        except Exception as e:
            self._log_error("Error during code quality checks", e)
            raise

    @staticmethod
    def _is_response_file(file: FileSpec) -> bool:
        """Check if the file is a response interface"""
        return GeneratedModel.is_response_file(file.path)
