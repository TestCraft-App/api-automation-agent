from typing import Any, List, Optional

import pydantic
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from src.models.api_verb import APIVerb

from .file_service import FileService
from ..ai_tools.file_creation_tool import FileCreationTool
from ..ai_tools.file_reading_tool import FileReadingTool
from ..ai_tools.models.file_spec import FileSpec, file_specs_to_json, convert_to_file_spec
from ..ai_tools.models.model_file_spec import convert_to_model_file_spec, ModelFileSpec
from ..configuration.config import Config
from ..configuration.data_sources import DataSource
from ..configuration.models import Model, ModelCost
from ..models import GeneratedModel, APIModel
from ..models.api_model import api_models_to_json
from ..models.usage_data import LLMCallUsageData, AggregatedUsageMetadata
from ..utils.logger import Logger

UsageMetadataPayload = LLMCallUsageData


class PromptConfig:
    """Configuration for prompt file paths."""

    DOT_ENV = "./prompts/create-dot-env.txt"
    MODELS = "./prompts/create-models.txt"
    FIRST_TEST = "./prompts/create-first-test.txt"
    FIRST_TEST_POSTMAN = "./prompts/create-first-test-postman.txt"
    TESTS = "./prompts/create-tests.txt"
    FIX_TYPESCRIPT = "./prompts/fix-typescript.txt"
    SUMMARY = "./prompts/generate-model-summary.txt"
    ADD_INFO = "./prompts/add-models-context.txt"
    ADDITIONAL_TESTS = "./prompts/create-additional-tests.txt"
    FIX_TEST = "./prompts/fix-test.txt"


class LLMService:
    """
    Service for managing language model interactions.
    """

    def __init__(
        self,
        config: Config,
        file_service: FileService,
    ):
        """
        Initialize LLM Service.

        Args:
            config (Config): Configuration object
            file_service (FileService): File service for file operations
        """
        self.config = config
        self.file_service = file_service
        self.logger = Logger.get_logger(__name__)
        self.aggregated_usage_metadata = AggregatedUsageMetadata()

    def get_aggregated_usage_metadata(self) -> AggregatedUsageMetadata:
        """Returns the aggregated LLM usage metadata Pydantic model instance."""
        return self.aggregated_usage_metadata

    def _select_language_model(
        self, language_model: Optional[Model] = None, override: bool = False
    ) -> BaseLanguageModel:
        """
        Select and configure the appropriate language model.

        Args:
            language_model (Optional[Model]): Optional model to use
            override (bool): Whether to override the default model

        Returns:
            BaseLanguageModel: Configured language model
        """
        try:
            if language_model and override:
                self.config.model = language_model
            if self.config.model.is_anthropic():
                return ChatAnthropic(
                    model_name=self.config.model.value,
                    temperature=1,
                    api_key=pydantic.SecretStr(self.config.anthropic_api_key),
                    timeout=None,
                    stop=None,
                    max_retries=3,
                    max_tokens_to_sample=8192,
                )
            return ChatOpenAI(
                model=self.config.model.value,
                temperature=1,
                max_retries=3,
                api_key=pydantic.SecretStr(self.config.openai_api_key),
            )
        except Exception as e:
            self.logger.error(f"Model initialization error: {e}")
            raise

    def _load_prompt(self, prompt_path: str) -> str:
        """
        Load a prompt from a file.

        Args:
            prompt_path (str): Path to the prompt file

        Returns:
            str: Loaded prompt content
        """
        try:
            with open(prompt_path, "r", encoding="utf-8") as file:
                return file.read().strip()
        except IOError as e:
            self.logger.error(f"Failed to load prompt from {prompt_path}: {e}")
            raise

    def _calculate_llm_call_cost(self, model_enum: Model, usage_data: LLMCallUsageData) -> Optional[float]:
        """Calculates the cost of a single LLM call based on token usage and model rates."""
        try:
            model_costs: ModelCost = model_enum.get_costs()
            input_cost = (usage_data.input_tokens / 1_000_000) * model_costs.input_cost_per_million_tokens
            output_cost = (usage_data.output_tokens / 1_000_000) * model_costs.output_cost_per_million_tokens
            return input_cost + output_cost
        except Exception as e:
            self.logger.error(f"Error calculating LLM call cost for model {model_enum.value}: {e}")
            return None

    def create_ai_chain(
        self,
        prompt_path: str,
        tools: Optional[List[BaseTool]] = None,
        must_use_tool: Optional[bool] = False,
        language_model: Optional[Model] = None,
    ) -> Any:
        """
        Create a flexible AI chain with tool support.

        Args:
            prompt_path (str): Path to the prompt template
            tools (Optional[List[BaseTool]]): Tools to bind
            must_use_tool (Optional[bool]): Whether to enforce tool usage
            language_model (Optional[Model]): Language model to use

        Returns:
            Any: Configured AI processing chain
        """
        try:
            all_tools = tools or []

            llm = self._select_language_model(language_model)
            prompt_template = ChatPromptTemplate.from_template(self._load_prompt(prompt_path))

            if tools:
                tool_choice = "auto"
                if self.config.model.is_anthropic():
                    if must_use_tool:
                        tool_choice = "any"
                else:
                    if must_use_tool:
                        tool_choice = "required"
                llm_with_tools = llm.bind_tools(all_tools, tool_choice=tool_choice)
            else:
                llm_with_tools = llm

            def process_response(response):
                if response.usage_metadata is not None:
                    try:
                        current_usage_metadata = LLMCallUsageData.model_validate(response.usage_metadata)
                        cost = self._calculate_llm_call_cost(self.config.model, current_usage_metadata)
                        current_usage_metadata.cost = cost
                        self.aggregated_usage_metadata.add_call_usage(current_usage_metadata)
                    except Exception as validation_error:
                        self.logger.warning(
                            f"Failed to validate usage metadata: {validation_error}. Using defaults."
                        )
                        current_usage_metadata = LLMCallUsageData()
                        self.aggregated_usage_metadata.add_call_usage(current_usage_metadata)
                else:
                    current_usage_metadata = LLMCallUsageData()
                    self.aggregated_usage_metadata.add_call_usage(current_usage_metadata)

                tool_map = {tool.name.lower(): tool for tool in all_tools}

                if response.tool_calls:
                    tool_call = response.tool_calls[0]
                    selected_tool = tool_map.get(tool_call["name"].lower())

                    if selected_tool:
                        return selected_tool.invoke(tool_call["args"])

                return response.content

            return prompt_template | llm_with_tools | process_response

        except Exception as e:
            self.logger.error(f"Chain creation error: {e}")
            raise

    def generate_dot_env(self, definition_content: str) -> None:
        """Generate .env file with environment variables."""
        self.create_ai_chain(
            PromptConfig.DOT_ENV,
            tools=[FileCreationTool(self.config, self.file_service)],
            must_use_tool=True,
        ).invoke({"api_definition": definition_content})

    def generate_models(self, definition_content: str) -> List[ModelFileSpec]:
        """Generate models for the API definition."""
        try:
            result = self.create_ai_chain(
                PromptConfig.MODELS,
                tools=[FileCreationTool(self.config, self.file_service, are_models=True)],
                must_use_tool=True,
            ).invoke({"api_definition": definition_content})
            return convert_to_model_file_spec(result)
        except Exception as e:
            self.logger.error(f"Error generating models: {str(e)}")
            return []

    def generate_first_test(self, definition_content: str, models: List[GeneratedModel]) -> List[FileSpec]:
        """Generate the first test for the API definition."""
        try:
            prompt = (
                PromptConfig.FIRST_TEST_POSTMAN
                if self.config.data_source == DataSource.POSTMAN
                else PromptConfig.FIRST_TEST
            )
            result = self.create_ai_chain(
                prompt,
                tools=[FileCreationTool(self.config, self.file_service)],
                must_use_tool=True,
            ).invoke({"api_definition": definition_content, "models": GeneratedModel.list_to_json(models)})
            return convert_to_file_spec(result)
        except Exception as e:
            self.logger.error(f"Error generating test: {e}")
            return []

    def get_additional_models(
        self, relevant_models: List[GeneratedModel], available_models: List[APIModel], api_verb: APIVerb
    ) -> List[FileSpec]:
        """Trigger read file tool to decide what additional model info is needed"""
        self.logger.info("\nGetting additional models...")
        result = self.create_ai_chain(
            PromptConfig.ADD_INFO,
            tools=[FileReadingTool(self.config, self.file_service)],
            must_use_tool=True,
        ).invoke(
            {
                "relevant_models": GeneratedModel.list_to_json(relevant_models),
                "available_models": api_models_to_json(available_models),
                "api_verb": api_verb,
            }
        )
        return convert_to_file_spec(result)

    def generate_additional_tests(
        self,
        tests: List[FileSpec],
        models: List[GeneratedModel],
        definition_content: str,
    ) -> List[FileSpec]:
        """Generate additional tests based on the initial test and models."""
        result = self.create_ai_chain(
            PromptConfig.ADDITIONAL_TESTS,
            tools=[FileCreationTool(self.config, self.file_service)],
            must_use_tool=True,
        ).invoke(
            {
                "tests": file_specs_to_json(tests),
                "models": GeneratedModel.list_to_json(models),
                "api_definition": definition_content,
            }
        )
        return convert_to_file_spec(result)

    def fix_typescript(self, files: List[FileSpec], messages: List[str], are_models: bool = False) -> None:
        """
        Fix TypeScript files.

        Args:
            files (List[FileSpec]): List of files to fix
            messages (List[str]): Associated error messages
            are_models (bool): Whether the files are models
        """
        self.logger.info("\nFixing TypeScript files:")
        for file in files:
            self.logger.info(f"  - {file.path}")

        self.create_ai_chain(
            PromptConfig.FIX_TYPESCRIPT,
            tools=[FileCreationTool(self.config, self.file_service, are_models=are_models)],
            must_use_tool=True,
        ).invoke({"files": file_specs_to_json(files), "messages": messages})

    def fix_test(self, files: List[FileSpec], run_output: List[str]) -> None:
        """
        Improve test files based on run output.

        Args:
            files (List[FileSpec]): List of files to fix
            run_output (List[str]): HTTP activity/Reporter output
        """
        self.logger.info("\nFixing Test & Models:")
        for file in files:
            self.logger.info(f"  - {file.path}")

        self.create_ai_chain(
            PromptConfig.FIX_TEST,
            tools=[FileCreationTool(self.config, self.file_service)],
            must_use_tool=True,
        ).invoke({"files": file_specs_to_json(files), "run_output": run_output})
