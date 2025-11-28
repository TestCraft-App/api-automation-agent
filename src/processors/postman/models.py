from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class RequestData:
    """
    Represents one Postman request/test‐case with its metadata.
    """

    file_path: str
    root_path: str
    full_path: str
    verb: str
    body: Dict[str, Any]
    prerequest: List[str]
    script: List[str]
    name: str

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the RequestData object to a JSON-compatible dictionary.
        """
        return {
            "file_path": self.file_path,
            "root_path": self.root_path,
            "full_path": self.full_path,
            "verb": self.verb,
            "body": self.body,
            "prerequest": self.prerequest,
            "script": self.script,
            "name": self.name,
        }


@dataclass
class VerbInfo:
    """
    One (path, verb) combination with all its aggregated query‐params and body attributes.
    """

    verb: str
    root_path: str | None
    full_path: str
    query_params: Dict[str, str]
    body_attributes: Dict[str, Any]
    script: List[str]
