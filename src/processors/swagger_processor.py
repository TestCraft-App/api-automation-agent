import json
from typing import List, Optional

import yaml

from .swagger import (
    APIDefinitionMerger,
    APIDefinitionSplitter,
    APIDefinitionLoader,
    APIComponentsFilter,
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
        components_filter: APIComponentsFilter,
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
            components_filter (APIComponentsFilter): Service to filter API components.
            api_definition_loader (APIDefinitionLoader): Service to load API definition from URL or file.
        """
        self.config = config
        self.file_service = file_service
        self.file_loader = file_loader
        self.splitter = splitter
        self.merger = merger
        self.components_filter = components_filter
        self.api_definition_loader = api_definition_loader or APIDefinitionLoader()
        self.base_definition: str | None = None
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
            base_definition, split_definitions = self.splitter.split(raw_definition)
            merged_definitions = self.merger.merge(split_definitions)
            self.base_definition = base_definition

            result = APIDefinition(endpoints=self.config.endpoints, base_yaml=base_definition)
            for definition in merged_definitions:
                if not result.should_process_endpoint(definition.path):
                    self.logger.debug(f"Skipping endpoint: {definition.path}")
                    continue
                if isinstance(definition, APIPath):
                    result.add_definition(APIPath(path=definition.path, yaml=definition.yaml))
                elif isinstance(definition, APIVerb):
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

            if not result.definitions:
                if self.config.endpoints:
                    self.logger.error(
                        f"\n❌ The API definition does not contain any of the provided endpoints: {', '.join(self.config.endpoints)}"
                    )
                else:
                    self.logger.error("❌ No endpoints were found in the API definition.")
            else:
                self.logger.info(f"Successfully processed {len(result.definitions)} API definitions.")
            return result
        except Exception as e:
            self.logger.error(f"Error processing API definition: {e}")
            raise

    def create_dot_env(self, api_definition: APIDefinition) -> None:
        self.logger.info("\nGenerating .env file...")

        try:
            base_api_spec = json.loads(api_definition.base_yaml or "{}")
        except json.JSONDecodeError:
            base_api_spec = yaml.safe_load(api_definition.base_yaml or "{}")

        base_url = self._extract_base_url(base_api_spec)

        if not base_url:
            self.logger.warning("⚠️ Could not extract base URL from API definition")
            base_url = input("Please enter the base URL for the API: ")

        env_file_path = ".env"
        env_content = f"BASEURL={base_url}\n"

        file_spec = FileSpec(path=env_file_path, fileContent=env_content)
        self.file_service.create_files(self.config.destination_folder, [file_spec])

        self.logger.info(f"Generated .env file with BASEURL={base_url}")

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
        return api_definition.get_paths()

    def get_api_path_name(self, api_path: APIPath) -> str:
        return api_path.path

    def get_api_verbs(self, api_definition: APIDefinition) -> List[APIVerb]:
        """Get all verb definitions that should be processed."""
        return api_definition.get_verbs()

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
        return self._build_full_definition(api_verb.yaml)

    def get_api_path_content(self, api_path: APIPath) -> str:
        return self._build_full_definition(api_path.yaml)

    def _build_full_definition(self, paths_yaml: str) -> str:
        """Combine base specification with a partial paths YAML"""
        base_spec = yaml.safe_load(self.base_definition or "{}")
        paths_spec = yaml.safe_load(paths_yaml or "{}")
        base_spec["paths"] = paths_spec
        filtered_spec = self.components_filter.filter_schemas(base_spec)
        return yaml.dump(filtered_spec, sort_keys=False)
