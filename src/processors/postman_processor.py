import copy
import json
import os
from typing import Dict, List

from .postman.models import VerbInfo, RequestData
from ..ai_tools.models.file_spec import FileSpec
from ..models import APIModel, APIVerb, GeneratedModel, ModelInfo, APIDefinition
from ..processors.api_processor import APIProcessor
from ..processors.postman.postman_utils import PostmanUtils
from ..services.file_service import FileService
from ..utils.logger import Logger


class PostmanProcessor(APIProcessor):
    """Processes Postman API definitions."""

    def __init__(self, file_service: FileService):
        self.file_service = file_service
        self.logger = Logger.get_logger(__name__)
        self.service_dict = {}

    def process_api_definition(self, api_definition_path: str) -> APIDefinition:
        with open(api_definition_path, encoding="utf-8") as f:
            data = json.load(f)
        return APIDefinition(PostmanUtils.extract_requests(data))

    def extract_env_vars(self, api_definition: APIDefinition) -> List[str]:
        return PostmanUtils.extract_env_vars(api_definition)

    def get_api_paths(self, api_definition: APIDefinition) -> List[Dict[str, List[VerbInfo]]]:
        # Get all distinct paths without query params
        distinct_paths = {item.path.split("?")[0] for item in api_definition.definitions}

        # Group paths by service
        paths_grouped_by_service = PostmanUtils.group_paths_by_service(distinct_paths)

        # Map verbs to services
        self.service_dict = PostmanUtils.map_verb_path_pairs_to_services(
            api_definition.definitions, paths_grouped_by_service
        )
        return [copy.deepcopy(self.service_dict)]

    def get_api_path_name(self, api_path: Dict[str, List[VerbInfo]]) -> str:
        keys = list(api_path.keys())
        return keys[0] if len(keys) > 0 else ""

    def get_relevant_models(self, all_models: List[ModelInfo], api_verb: RequestData) -> List[GeneratedModel]:
        """Get models relevant to the API verb."""
        result = []
        for model in all_models:
            if api_verb.service == model.path:
                result = [GeneratedModel(path=file.fileContent) for file in model.models]
        return result

    def get_other_models(self, all_models: List[ModelInfo], api_verb: RequestData) -> List[APIModel]:
        result: List[APIModel] = []
        for model in all_models:
            if model.path != api_verb.service:
                result.append(APIModel(path=model.path, files=model.files))
        return result

    def get_api_verb_path(self, api_verb: APIVerb) -> str:
        return api_verb.path

    def get_api_verb_rootpath(self, api_verb: RequestData) -> str:
        return api_verb.service

    def get_api_verb_name(self, api_verb: APIVerb) -> str:
        return api_verb.verb

    def get_api_verbs(self, api_definition: APIDefinition) -> List[APIVerb]:
        verb_chunks_tagged_with_service = copy.deepcopy(api_definition.definitions)

        for verb_chunk in verb_chunks_tagged_with_service:
            for service, verbs in self.service_dict.items():
                routes_in_service = [verb.path for verb in verbs]
                verb_chunk_path_no_query_params = verb_chunk.path.split("?")[0]

                if verb_chunk_path_no_query_params in routes_in_service:
                    verb_chunk.service = service
                    break

        return verb_chunks_tagged_with_service

    def get_api_verb_content(self, api_verb: RequestData) -> str:
        return json.dumps(api_verb.to_json())

    def get_api_path_content(self, api_path: Dict[str, List[VerbInfo]]) -> str:
        content = {}
        for service, verbs in api_path.items():
            content[service] = []
            for verb in verbs:
                content[service].append(
                    {
                        "path": verb.path,
                        "verb": verb.verb,
                        "query_params": verb.query_params,
                        "body_attributes": verb.body_attributes,
                        "root_path": verb.root_path,
                    }
                )
        return json.dumps(content)

    def update_framework_for_postman(self, destination_folder: str, api_definition: APIDefinition):
        self._create_run_order_file(destination_folder, api_definition)
        self._update_package_dot_json(destination_folder)

    def _update_package_dot_json(self, destination_folder: str):
        pkg = os.path.join(destination_folder, "package.json")
        try:
            with open(pkg, "r") as f:
                data = json.load(f)
            data.setdefault("scripts", {})["test"] = "mocha runTestsInOrder.js --timeout 10000"
            with open(pkg, "w") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Updated package.json at {pkg}")
        except Exception as e:
            self.logger.error(f"Failed to update package.json: {e}")

    def _create_run_order_file(self, destination_folder: str, api_definition: APIDefinition):
        lines = ["// This file runs the tests in order"]
        for definition in api_definition.definitions:
            if isinstance(definition, APIVerb):
                lines.append(f'import "./{definition.path}.spec.ts";')
        file_spec = FileSpec(path="runTestsInOrder.js", fileContent="\n".join(lines))
        self.file_service.create_files(destination_folder, [file_spec])
        self.logger.info(f"Created runTestsInOrder.js at {destination_folder}")
