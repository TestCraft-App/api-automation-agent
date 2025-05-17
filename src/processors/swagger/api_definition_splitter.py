import copy
import re
from typing import Dict, List

import yaml

from ...models import APIPath, APIVerb, APIDef
from ...utils.logger import Logger


class APIDefinitionSplitter:
    """Splits API definitions into smaller components."""

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def split(self, api_definition: Dict) -> List[APIDef]:
        """Splits the API definition into smaller, manageable parts."""
        self.logger.info("Splitting API definition into components...")
        api_definition_list = []

        for path, path_data in api_definition.get("paths", {}).items():
            normalized_path = APIPath.normalize_path(path)

            path_copy = copy.deepcopy(api_definition)
            path_copy["paths"] = {path: path_data}
            api_definition_list.append(
                APIPath(path=normalized_path, yaml=yaml.dump(path_copy, sort_keys=False))
            )

            for verb, verb_data in path_data.items():
                verb_copy = copy.deepcopy(path_copy)
                verb_copy["paths"][path] = {verb: verb_data}
                api_definition_list.append(
                    APIVerb(
                        verb=verb.upper(),
                        path=normalized_path,
                        root_path=APIVerb.get_root_path(normalized_path),
                        yaml=yaml.dump(verb_copy, sort_keys=False),
                    )
                )

        self.logger.info("Successfully split API definition.")
        return api_definition_list

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalizes the path by removing api and version prefixes."""
        parts = [p for p in path.split("/") if p]

        if not parts:
            return path

        start_index = 0

        if start_index < len(parts):
            if parts[start_index] == "api":
                start_index += 1

        if start_index < len(parts):
            if (
                parts[start_index].startswith("v")
                and len(parts[start_index]) > 1
                and parts[start_index][1:].isdigit()
            ):
                start_index += 1

        if start_index < len(parts):
            return "/" + "/".join(parts[start_index:])
        return path

    @staticmethod
    def _get_root_path(path: str) -> str:
        """Gets the root path from a full path."""
        match = re.match(r"(/[^/?]+)", path)
        if match:
            return match.group(1)
        return path
