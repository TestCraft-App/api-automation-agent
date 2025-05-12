import json
import os
from typing import List

from src.ai_tools.models.file_spec import FileSpec
from src.processors.api_processor import APIProcessor
from src.models import APIModel, APIPath, APIVerb, GeneratedModel, ModelInfo, APIDefinition
from src.processors.postman.postman_utils import PostmanUtils
from src.services.file_service import FileService
from src.utils.logger import Logger


class PostmanProcessor(APIProcessor):
    """Processes Postman API definitions."""

    def __init__(self, file_service: FileService):
        self.file_service = file_service
        self.logger = Logger.get_logger(__name__)

    def process_api_definition(self, json_file_path: str) -> APIDefinition:
        with open(json_file_path, encoding="utf-8") as f:
            data = json.load(f)
        requests = PostmanUtils.extract_requests(data)
        verbs = PostmanUtils.extract_verb_path_info(requests)

        result = APIDefinition()
        for verb in verbs:
            result.add_definition(
                APIVerb(
                    verb=verb.verb,
                    path=verb.path,
                    root_path=verb.root_path,
                    yaml=json.dumps({"verb": verb.verb, "path": verb.path}),
                )
            )
        return result

    def extract_env_vars(self, api_definition: APIDefinition) -> List[str]:
        return PostmanUtils.extract_env_vars(api_definition)

    def get_api_paths(self, api_definition: APIDefinition) -> List[APIPath]:
        # Build VerbInfo list
        verbs = PostmanUtils.extract_verb_path_info(api_definition.definitions)
        # Build ServiceVerbs
        paths = [r.path.split("?", 1)[0] for r in api_definition.definitions]
        sv = PostmanUtils.map_verb_path_pairs_to_services(verbs, paths)

        result = []
        for service in sv:
            result.append(APIPath(path=service.service, yaml=json.dumps({"path": service.service})))
        return result

    def get_api_path_name(self, api_path: APIPath) -> str:
        return api_path.path

    def get_relevant_models(self, all_models: List[ModelInfo], api_verb: APIVerb) -> List[GeneratedModel]:
        """Get models relevant to the API verb."""
        try:
            self.logger.info(f"Getting relevant models for {api_verb.path} {api_verb.verb}")

            # Find the model info for this path
            path_model_info = next(
                (info for info in all_models if info.path == api_verb.path), ModelInfo(path=api_verb.path)
            )

            # Get models by path
            relevant_models = path_model_info.get_models_by_path(api_verb.path)

            # If no models found by path, try to find by summary
            if not relevant_models:
                relevant_models = path_model_info.get_models_by_summary(api_verb.verb.lower())

            self.logger.info(
                f"Found {len(relevant_models)} relevant models for {api_verb.path} {api_verb.verb}"
            )
            return relevant_models

        except Exception as e:
            self.logger.error(f"Error getting relevant models: {str(e)}")
            return []

    def get_other_models(
        self,
        all_models: List[ModelInfo],
        verb: APIVerb,
    ) -> List[APIModel]:
        result = []
        for model in all_models:
            if model.path != verb.root_path:
                result.append(APIModel(path=model.path, files=model.files))
        return result

    def get_api_verb_path(self, verb: APIVerb) -> str:
        return verb.path

    def get_api_verb_rootpath(self, verb: APIVerb) -> str:
        return verb.root_path

    def get_api_verb_name(self, verb: APIVerb) -> str:
        return verb.verb

    def get_api_verbs(self, api_definition: APIDefinition) -> List[APIVerb]:
        return api_definition.get_verbs()

    def get_api_verb_content(self, verb: APIVerb) -> str:
        return verb.yaml

    def get_api_path_content(self, svc: APIPath) -> str:
        return svc.yaml

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
