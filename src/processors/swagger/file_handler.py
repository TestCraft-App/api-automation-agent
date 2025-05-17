import json
from typing import Dict

import yaml

from ...utils.logger import Logger


class FileLoader:
    """Handles loading API definitions from files."""

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def load(self, file_path: str) -> Dict:
        """Loads a YAML or JSON file and returns its content."""
        try:
            self.logger.info("Loading API definition from...")
            with open(file_path, "r") as file:
                if file_path.endswith((".yml", ".yaml")):
                    return yaml.safe_load(file)
                elif file_path.endswith(".json"):
                    return json.load(file)
                else:
                    raise ValueError("Unsupported file format")
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            raise
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            self.logger.error(f"Error parsing file {file_path}: {e}")
            raise
