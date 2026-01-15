import json
import os
import re
from typing import Dict, List

from src.models.api_path import APIPath
from src.models.api_verb import APIVerb

from ..configuration.config import Config

from ..ai_tools.models.file_spec import FileSpec
from ..models import APIModel, GeneratedModel, ModelInfo, APIDefinition
from ..processors.api_processor import APIProcessor
from ..processors.postman.postman_utils import PostmanUtils
from ..services.file_service import FileService
from ..utils.logger import Logger


class PostmanProcessor(APIProcessor):
    """Processes Postman API definitions."""

    def __init__(self, file_service: FileService, config: Config):
        self.file_service = file_service
        self.config = config
        self.logger = Logger.get_logger(__name__)

    def process_api_definition(self, api_definition_path: str) -> APIDefinition:
        with open(api_definition_path, encoding="utf-8") as f:
            data = json.load(f)
        requests = PostmanUtils.extract_requests(data, prefixes=self.config.prefixes)
        variables = PostmanUtils.extract_variables(data)

        collection_name = (data.get("info") or {}).get("name")
        return APIDefinition(definitions=requests, variables=variables, name=collection_name)

    def create_dot_env(self, api_definition: APIDefinition) -> None:
        self.logger.info("\nGenerating .env file...")
        env_vars = api_definition.variables

        if not env_vars:
            self.logger.warning("⚠️ No environment variables found in Postman collection")
            env_vars = [{"key": "BASEURL", "value": ""}]

        # Also include placeholders for any Postman template variables referenced in URLs/bodies,
        # since those frequently come from a Postman Environment (not embedded in the collection).
        template_var_names: set[str] = set()
        try:
            for verb in api_definition.definitions or []:
                full_path = getattr(verb, "full_path", "") or ""
                raw_body = getattr(verb, "raw_body", "") or ""
                for text in (full_path, raw_body):
                    for m in re.findall(r"{{\s*([A-Za-z0-9_]+)\s*}}", text):
                        template_var_names.add(m)
        except Exception as e:
            self.logger.debug(f"Could not extract template vars for .env: {e}")

        def to_env_key(key: str) -> str:
            k = (key or "").strip()
            if k.lower() in {"base_url", "baseurl", "base-url", "base url"}:
                return "BASEURL"
            return k.upper()

        existing_keys = {to_env_key(var.get("key", "")) for var in env_vars if isinstance(var, dict)}
        for name in sorted(template_var_names):
            key = to_env_key(name)
            if key and key not in existing_keys:
                env_vars.append({"key": key, "value": ""})
                existing_keys.add(key)

        env_content = "\n".join(f"{to_env_key(var['key'])}={var['value']}" for var in env_vars) + "\n"
        file_spec = FileSpec(path=".env", fileContent=env_content)
        self.file_service.create_files(self.config.destination_folder, [file_spec])
        self.logger.info(
            f"Generated .env file with variables: {', '.join(to_env_key(var['key']) for var in env_vars)}"
        )

    def get_api_paths(self, api_definition: APIDefinition) -> List[APIPath]:
        """Create APIPath objects from APIVerbs and group by service."""
        requests_by_service = PostmanUtils.group_request_data_by_service(api_definition.definitions)
        api_paths: List[APIPath] = []

        service_dict: Dict[str, List[APIVerb]] = {}
        for service, service_requests in requests_by_service.items():
            verb_infos = PostmanUtils.extract_verb_path_info(service_requests)
            service_dict[service] = verb_infos

            if not verb_infos:
                return json.dumps({})

            content = {service: []}
            for verb in verb_infos:
                content[service].append(
                    {
                        "root_path": verb.root_path,
                        "full_path": verb.full_path,
                        "verb": verb.verb,
                        "query_params": verb.query_params,
                        "body_attributes": verb.body_attributes,
                        "script": verb.script,
                    }
                )
            api_paths.append(APIPath(root_path=service, content=json.dumps(content)))
        return api_paths

    def get_api_path_name(self, api_path: APIPath) -> str:
        return api_path.root_path

    def get_relevant_models(self, all_models: List[ModelInfo], api_verb: APIVerb) -> List[GeneratedModel]:
        """Get models relevant to the API verb."""
        result: List[GeneratedModel] = []
        for model in all_models:
            if api_verb.root_path == model.path:
                result.extend(model.models)
        return result

    def get_other_models(self, all_models: List[ModelInfo], api_verb: APIVerb) -> List[APIModel]:
        result: List[APIModel] = []
        for model in all_models:
            if model.path != api_verb.root_path:
                result.append(APIModel(path=model.path, files=model.files))
        return result

    def get_api_verb_path(self, api_verb: APIVerb) -> str:
        return api_verb.full_path

    def get_api_verb_rootpath(self, api_verb: APIVerb) -> str:
        return api_verb.root_path

    def get_api_verb_name(self, api_verb: APIVerb) -> str:
        return api_verb.verb

    def get_api_verbs(self, api_definition: APIDefinition) -> List[APIVerb]:
        """Return all APIVerbs from the API definition"""
        return [d for d in api_definition.definitions if isinstance(d, APIVerb)]

    def get_api_verb_content(self, api_verb: APIVerb) -> str:
        return json.dumps(
            {
                "file_path": api_verb.file_path,
                "root_path": api_verb.root_path,
                "full_path": api_verb.full_path,
                "verb": api_verb.verb,
                "body": api_verb.body,
                "prerequest": api_verb.prerequest,
                "script": api_verb.script,
                "name": api_verb.name,
            }
        )

    def get_api_path_content(self, api_path: APIPath) -> str:
        return api_path.content

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
        def sanitize(name: str) -> str:
            n = (name or "").strip().lower()
            n = re.sub(r"[^a-z0-9]+", "-", n)
            n = re.sub(r"-+", "-", n).strip("-")
            return n or "api-collection"

        # Postman generation emits a single collection spec under src/tests.
        collection_name = getattr(api_definition, "name", None) or "api-collection"
        spec_base = sanitize(collection_name)
        spec_path = f"./src/tests/{spec_base}.spec.ts"
        lines = ["// This file runs the tests in order", f'import "{spec_path}";']
        file_spec = FileSpec(path="runTestsInOrder.js", fileContent="\n".join(lines))
        self.file_service.create_files(destination_folder, [file_spec])
        self.logger.info(f"Created runTestsInOrder.js at {destination_folder}")
