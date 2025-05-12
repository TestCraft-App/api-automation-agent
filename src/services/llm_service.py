from typing import Any, Dict, List, Optional

import pydantic
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from src.configuration.models import Model
from .file_service import FileService
from ..ai_tools.file_creation_tool import FileCreationTool
from ..ai_tools.file_reading_tool import FileReadingTool
from ..configuration.config import Config
from ..utils.logger import Logger
from src.ai_tools.models.file_spec import FileSpec
from src.models import APIModel, GeneratedModel
from src.models.model_info import ModelInfo
from src.models.api_path import APIPath


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
        """
        self.config = config
        self.file_service = file_service
        self.logger = Logger.get_logger(__name__)

    def _select_language_model(
        self, language_model: Optional[Model] = None, override: bool = False
    ) -> ChatOpenAI | ChatAnthropic:
        """
        Select and configure the appropriate language model.

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
            language_model (Optional[BaseLanguageModel]): Language model to use

        Returns:
            Configured AI processing chain
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

    def generate_models(self, api_definition: APIPath) -> List[GeneratedModel]:
        """Generate models for the API definition."""
        try:
            self.logger.info(f"Generating models for {api_definition.path}")
            model_info = ModelInfo(path=api_definition.path)

            # Generate models using LLM
            response = self._generate_with_llm(
                api_definition.yaml, self.prompt_config.model_generation_prompt
            )

            if not response:
                self.logger.warning(f"No models generated for {api_definition.path}")
                return []

            # Parse and create models
            for model_data in response:
                model = GeneratedModel(
                    path=model_data["path"],
                    fileContent=model_data["fileContent"],
                    summary=model_data["summary"],
                )
                model_info.add_model(model)

            self.logger.info(f"Generated {len(model_info.models)} models for {api_definition.path}")
            return model_info.models

        except Exception as e:
            self.logger.error(f"Error generating models: {str(e)}")
            return []

    def generate_first_test(
        self, api_definition: APIPath, models: List[GeneratedModel]
    ) -> List[GeneratedModel]:
        """Generate the first test for the API definition."""
        try:
            self.logger.info(f"Generating first test for {api_definition.path}")
            model_info = ModelInfo(path=f"{api_definition.path}/tests")

            # Generate test using LLM
            response = self._generate_with_llm(
                api_definition.yaml,
                self.prompt_config.test_generation_prompt,
                models=[model.to_json() for model in models],
            )

            if not response:
                self.logger.warning(f"No test generated for {api_definition.path}")
                return []

            # Parse and create test model
            test_model = GeneratedModel(
                path=response[0]["path"],
                fileContent=response[0]["fileContent"],
                summary=response[0]["summary"],
            )
            model_info.add_model(test_model)

            self.logger.info(f"Generated test for {api_definition.path}")
            return model_info.models

        except Exception as e:
            self.logger.error(f"Error generating test: {str(e)}")
            return []

    def get_additional_models(
        self,
        relevant_models: List[GeneratedModel],
        available_models: List[APIModel],
    ) -> List[FileSpec]:
        """Trigger read file tool to decide what additional model info is needed"""
        self.logger.info("\nGetting additional models...")
        return self.create_ai_chain(
            PromptConfig.ADD_INFO,
            tools=[FileReadingTool(self.config, self.file_service)],
            must_use_tool=True,
        ).invoke(
            {
                "relevant_models": [model.to_json() for model in relevant_models],
                "available_models": [model.to_json() for model in available_models],
            }
        )

    def generate_additional_tests(
        self,
        tests: List[FileSpec],
        models: List[GeneratedModel],
        api_definition: str,
    ) -> List[FileSpec]:
        """Generate additional tests based on the initial test and models."""
        return self.create_ai_chain(
            PromptConfig.ADDITIONAL_TESTS,
            tools=[FileCreationTool(self.config, self.file_service)],
            must_use_tool=True,
        ).invoke(
            {
                "tests": tests,
                "models": [model.to_json() for model in models],
                "api_definition": api_definition,
            }
        )

    def generate_dot_env(self, env_vars: List[str]) -> None:
        """Generate .env file with environment variables."""
        self.create_ai_chain(
            PromptConfig.DOT_ENV,
            tools=[FileCreationTool(self.config, self.file_service)],
            must_use_tool=True,
        ).invoke({"env_vars": env_vars})

    def fix_typescript(
        self, files: List[Dict[str, str]], messages: List[str], are_models: bool = False
    ) -> None:
        """
        Fix TypeScript files.

        Args:
            files (List[Dict[str, str]]): Files to fix
            messages (List[str]): Associated error messages
            are_models (bool): Whether the files are models
        """
        self.logger.info("\nFixing TypeScript files:")
        for file in files:
            self.logger.info(f"  - {file['path']}")

        self.create_ai_chain(
            PromptConfig.FIX_TYPESCRIPT,
            tools=[FileCreationTool(self.config, self.file_service, are_models=are_models)],
            must_use_tool=True,
        ).invoke({"files": files, "messages": messages})
