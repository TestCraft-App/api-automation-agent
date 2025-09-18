import signal
import sys
import traceback
from typing import List, Dict, Optional, cast

from src.models.fix_result import FixResult

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
        except OSError as e:
            self.logger.error(f"File system error while saving state: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while saving state: {e}")
        sys.exit(1)

    def _log_error(self, message: str, exc: Exception):
        """Helper method to log errors consistently"""
        self.logger.error(f"{message}: {exc}")

    def get_aggregated_usage_metadata(self) -> AggregatedUsageMetadata:
        """Returns the aggregated LLM usage metadata Pydantic model instance."""
        return self.llm_service.get_aggregated_usage_metadata()

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
            self.api_processor.create_dot_env(api_definition)
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
                    self.logger.debug(
                        "Generated models for path: " + self.api_processor.get_api_path_name(path)
                    )

            if generate_tests in (
                GenerationOptions.MODELS_AND_FIRST_TEST,
                GenerationOptions.MODELS_AND_TESTS,
            ):
                for verb in self.checkpoint.checkpoint_iter(api_verbs, "generate_verbs"):
                    service_related_to_verb = self.api_processor.get_api_verb_rootpath(verb)
                    tests = self._generate_tests(verb, all_generated_models["info"], generate_tests)
                    if not tests:
                        tests = []
                    for file in filter(self._is_response_file, tests):
                        for model in all_generated_models["info"]:
                            if model.path == service_related_to_verb:
                                model.files.append(file.path)
                                model.models.append(
                                    GeneratedModel(path=file.path, fileContent=file.fileContent, summary="")
                                )
                    verb_path_for_debug = self.api_processor.get_api_verb_path(verb)
                    verb_name_for_debug = self.api_processor.get_api_verb_name(verb)
                    self.logger.debug(
                        f"Generated tests for path: {verb_path_for_debug} - {verb_name_for_debug}"
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

    def _generate_models(self, api_definition: APIPath | str) -> Optional[List[GeneratedModel]]:
        """Generate models for the API definition."""
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
            self.logger.info(f"Generated {len(models_result)} models for {path_name}")
            return GeneratedModel.from_model_file_specs(models_result)

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
        verb_path = self.api_processor.get_api_verb_path(api_verb)
        verb_name = self.api_processor.get_api_verb_name(api_verb)
        try:
            relevant_models = self.api_processor.get_relevant_models(all_models, api_verb)
            other_models = self.api_processor.get_other_models(all_models, api_verb)
            self.logger.info(f"\nGenerating first test for path: {verb_path} and verb: {verb_name}")

            if other_models:
                additional_models_result = self.llm_service.get_additional_models(
                    relevant_models, other_models
                )
                if additional_models_result:
                    model_paths = [m.path for m in additional_models_result if hasattr(m, "path")]
                    self.logger.info(f"\nAdding additional models: {model_paths}")
                    for model in additional_models_result:
                        generated_model = GeneratedModel(
                            path=model.path,
                            fileContent=model.fileContent,
                        )
                        relevant_models.append(generated_model)

            tests_result = self.llm_service.generate_first_test(
                self.api_processor.get_api_verb_content(api_verb),
                relevant_models,
            )

            if tests_result:
                self.test_files_count += len(tests_result)
                self.save_state()
                model_file_specs = [FileSpec(path=m.path, fileContent=m.fileContent) for m in relevant_models]
                fixed_tests = self._run_code_quality_checks(tests_result + model_file_specs)
                if generate_tests == GenerationOptions.MODELS_AND_TESTS:
                    additional_tests_result = self._generate_additional_tests(
                        fixed_tests,
                        relevant_models,
                        api_verb,
                    )
                    return additional_tests_result

                return fixed_tests
            else:
                self.logger.warning(f"No tests generated for {verb_path} - {verb_name}")
                return None
        except Exception as e:
            self._log_error(f"Error processing verb definition for {verb_path} - {verb_name}", e)
            raise

    def _generate_additional_tests(
        self,
        tests: List[FileSpec],
        models: List[GeneratedModel | str],
        api_definition: APIVerb,
    ) -> Optional[List[FileSpec]]:
        """Generate additional tests based on the initial test and models"""
        verb_path = self.api_processor.get_api_verb_path(api_definition)
        verb_name = self.api_processor.get_api_verb_name(api_definition)
        try:
            self.logger.info(f"\nGenerating additional tests for path: {verb_path} and verb: {verb_name}")
            additional_tests_result = self.llm_service.generate_additional_tests(
                tests, models, self.api_processor.get_api_verb_content(api_definition)
            )
            if additional_tests_result:
                if len(additional_tests_result) > len(tests):
                    self.test_files_count += len(additional_tests_result) - len(tests)

                self.save_state()
                fixed_tests = self._run_code_quality_checks(additional_tests_result + models)
                return fixed_tests
            return tests
        except Exception as e:
            self._log_error(
                f"Error generating additional tests for {verb_path} - {verb_name}\n{traceback.format_exc()}",
                e,
            )
            return tests

    def _run_code_quality_checks(self, files: List[FileSpec], are_models: bool = False) -> List[FileSpec]:
        """
        Runs code quality checks on the provided files, including TypeScript compilation, execution check, linting, and formatting.
        Args:
            files (List[FileSpec]): A list of file specifications to check and fix.
            are_models (bool, optional): Indicates whether the files are models or tests. Defaults to False.
        Returns:
            List[FileSpec]: A list of files that were created or modified by the automatic quality checks.
        Raises:
            Exception: If any error occurs during the code quality checks, it is logged and the exception is raised.
        """
        error_type = "models" if are_models else "tests"
        fixed_files: List[FileSpec] = list(files or [])

        try:
            fixed_files = self.command_service.run_command_with_fix(
                command_func=self.command_service.run_typescript_compiler_for_files,
                fix_func=self._typescript_fix_wrapper,
                files=fixed_files,
                are_models=are_models,
            )

            if not are_models:
                fixed_files = self.command_service.run_command_with_fix(
                    command_func=self.command_service.run_test,
                    fix_func=self._test_fix_wrapper,
                    files=fixed_files,
                    max_retries=self.config.max_test_fixes,
                )

            self.command_service.format_files()
            self.command_service.run_linter()

            return fixed_files
        except Exception as e:
            self._log_error(f"Error during code quality checks for {error_type}", e)

    def _test_fix_wrapper(
        self, files: List[FileSpec], messages: str, fix_history: List[str], are_models: bool
    ) -> FixResult:
        self.logger.info("\nAttempting to fix Test errors with LLM...\n")
        fixed_files, changes, stop = self.llm_service.fix_test_execution(
            files,
            messages,
            fix_history,
        )
        all_fixes = list(fix_history)
        if changes:
            all_fixes.append(changes)

        self.logger.info("🛠️  Fix history:\n" + "\n".join(f"🔧 - {change}" for change in all_fixes))
        self.logger.info("Fix attempt complete.")

        if stop:
            self.logger.info(f"\n🛑 Stopping further fixes, reason: {stop.reason}\n")
            self.logger.info(f"📝 Details: {stop.content}")
            return fixed_files, changes, True

        return fixed_files, changes, False

    def _typescript_fix_wrapper(
        self, files: List[FileSpec], messages: str, fix_history: List[str], are_models: bool
    ) -> FixResult:
        self.logger.info("\nAttempting to fix TypeScript errors with LLM...")
        fixed_files = self.llm_service.fix_typescript(files, messages, are_models)
        self.logger.info("TypeScript fixing attempt complete.")
        return fixed_files, None, False

    @staticmethod
    def _is_response_file(file: FileSpec) -> bool:
        """Check if the file is a response interface"""
        return GeneratedModel.is_response_file(file.path)
