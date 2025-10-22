import copy
from typing import Dict, List, Optional, Tuple

import yaml

from ...models import APIPath, APIVerb, APIDef
from ...utils.logger import Logger


class APIDefinitionSplitter:
    """Splits API definitions into smaller components."""

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def split(self, api_definition: Dict, prefixes: Optional[List[str]] = None) -> Tuple[str, List[APIDef]]:
        """Splits the API definition into base and path/verb components."""
        self.logger.info("Splitting API definition into components...")
        api_definition_list: List[APIDef] = []

        base_definition = copy.deepcopy(api_definition)
        base_definition.pop("paths", None)
        base_yaml = yaml.dump(base_definition, sort_keys=False)

        for path, path_data in api_definition.get("paths", {}).items():
            normalized_path = APIPath.normalize_path(path, prefixes)

            api_definition_list.append(
                APIPath(path=normalized_path, yaml=yaml.dump({path: path_data}, sort_keys=False))
            )

            for verb, verb_data in path_data.items():
                api_definition_list.append(
                    APIVerb(
                        verb=verb.upper(),
                        path=normalized_path,
                        root_path=APIVerb.get_root_path(normalized_path),
                        yaml=yaml.dump({path: {verb: verb_data}}, sort_keys=False),
                    )
                )

        self.logger.info("Successfully split API definition.")
        return base_yaml, api_definition_list
