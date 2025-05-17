import json
from typing import List, Optional

import yaml

from .swagger import (
    APIDefinitionMerger,
    APIDefinitionSplitter,
    APIDefinitionLoader,
)
from ..ai_tools.models.file_spec import FileSpec
from ..configuration.config import Config
from ..models import APIModel, APIPath, APIVerb, GeneratedModel, ModelInfo, APIDefinition
from ..processors.api_processor import APIProcessor
from ..services.file_service import FileService
from ..utils.logger import Logger


class SwaggerProcessor(APIProcessor):
    """Processes API definitions by orchestrating file loading, splitting, and merging."""

    def __init__(
        self,
        file_loader: FileService,
        splitter: APIDefinitionSplitter,
        merger: APIDefinitionMerger,
        file_service: FileService,
        config: Config,
        api_definition_loader: Optional[APIDefinitionLoader] = None,
    ):
        """
        Initialize the SwaggerProcessor.

        Args:
            file_loader (FileLoader): Service to load API definition files.
            splitter (APIDefinitionSplitter): Service to split API definitions.
            merger (APIDefinitionMerger): Service to merge API definitions.
            api_definition_loader (APIDefinitionLoader): Service to load API definition from URL or file.
        """
        self.config = config
        self.file_service = file_service
        self.file_loader = file_loader
        self.splitter = splitter
        self.merger = merger
        self.api_definition_loader = api_definition_loader or APIDefinitionLoader()
        self.logger = Logger.get_logger(__name__)

    def process_api_definition(self, api_definition_path: str) -> APIDefinition:
        """
        Processes an API definition by loading, splitting, and merging its components.

        Args:
            api_definition_path (str): URL or path to the API definition.

        Returns:
            APIDefinition containing the processed API definitions.
        """
        try:
            self.logger.info("Starting API processing")
            raw_definition = self.api_definition_loader.load(api_definition_path)
            split_definitions = self.splitter.split(raw_definition)
            merged_definitions = self.merger.merge(split_definitions)

            result = APIDefinition(endpoints=self.config.endpoints)
            for definition in merged_definitions:
                if definition.type == "path":
                    result.add_definition(APIPath(path=definition.path, yaml=definition.yaml))
                elif definition.type == "verb":
                    result.add_definition(
                        APIVerb(
                            verb=definition.verb,
                            path=definition.path,
                            root_path=APIVerb.get_root_path(definition.path),
                            yaml=definition.yaml,
                        )
                    )

                self.logger.debug(f"\nType: {definition.type}")
                self.logger.debug(f"Path: {definition.path}")
                if isinstance(definition, APIVerb):
                    self.logger.debug(f"Verb: {definition.verb}")

            self.logger.info("Successfully processed API definition.")
            return result
        except Exception as e:
            self.logger.error(f"Error processing API definition: {e}")
            raise

    def extract_env_vars(self, api_definition: APIDefinition) -> list[str]:
        self.logger.info("\nGenerating .env file...")

        api_definition_str = api_definition.definitions[0].yaml
        try:
            api_spec = json.loads(api_definition_str)
        except json.JSONDecodeError:
            api_spec = yaml.safe_load(api_definition_str)

        base_url = self._extract_base_url(api_spec)

        if not base_url:
            self.logger.warning("⚠️ Could not extract base URL from API definition")
            base_url = input("Please enter the base URL for the API: ")

        env_file_path = ".env"
        env_content = f"BASEURL={base_url}\n"

        file_spec = FileSpec(path=env_file_path, fileContent=env_content)
        self.file_service.create_files(self.config.destination_folder, [file_spec])

        self.logger.info(f"Generated .env file with BASEURL={base_url}")
        return []

    @staticmethod
    def _extract_base_url(api_spec):
        """Extract base URL from OpenAPI specification"""
        if "openapi" in api_spec and api_spec["openapi"].startswith("3."):
            if "servers" in api_spec and api_spec["servers"] and "url" in api_spec["servers"][0]:
                return api_spec["servers"][0]["url"]
        elif "swagger" in api_spec and api_spec["swagger"].startswith("2."):
            host = api_spec.get("host")
            if host:
                scheme = "https"
                if "schemes" in api_spec and api_spec["schemes"]:
                    scheme = api_spec["schemes"][0]

                base_path = api_spec.get("basePath", "")
                return f"{scheme}://{host}{base_path}"

        return None

    def get_api_paths(self, api_definition: APIDefinition) -> List[APIPath]:
        """Get all path definitions that should be processed."""
        return api_definition.get_filtered_paths()

    def get_api_path_name(self, api_path: APIPath) -> str:
        return api_path.path

    def get_api_verbs(self, api_definition: APIDefinition) -> List[APIVerb]:
        """Get all verb definitions that should be processed."""
        return api_definition.get_filtered_verbs()

    def get_api_verb_path(self, api_verb: APIVerb) -> str:
        return api_verb.path

    def get_api_verb_rootpath(self, api_verb: APIVerb) -> str:
        return api_verb.root_path

    def get_api_verb_name(self, api_verb: APIVerb) -> str:
        return api_verb.verb

    def get_relevant_models(self, all_models: List[ModelInfo], api_verb: APIVerb) -> List[GeneratedModel]:
        """Get models relevant to the API verb."""
        result: List[GeneratedModel] = []

        for model in all_models:
            if api_verb.path == model.path or str(api_verb.path).startswith(model.path + "/"):
                result.extend(model.models)

        return result

    def get_other_models(
        self,
        all_models: List[ModelInfo],
        api_verb: APIVerb,
    ) -> List[APIModel]:
        result = []
        for model in all_models:
            if not (api_verb.path == model.path or str(api_verb.path).startswith(model.path + "/")):
                result.append(APIModel(path=model.path, files=model.files))
        return result

    def get_api_verb_content(self, api_verb: APIVerb) -> str:
        return api_verb.yaml

    def get_api_path_content(self, api_path: APIPath) -> str:
        return api_path.yaml
