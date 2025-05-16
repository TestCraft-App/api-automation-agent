from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RequestData:
    """
    Represents one Postman request/test‐case with its metadata.
    """

    service: str
    file_path: str
    path: str
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
            "service": self.service,
            "file_path": self.file_path,
            "path": self.path,
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
    path: str
    query_params: Dict[str, str]
    body_attributes: Dict[str, Any]
    root_path: str | None


@dataclass
class ServiceVerbs:
    """
    A collection of VerbInfo objects belonging to the same service root.
    """

    service: str
    verbs: List[VerbInfo] = field(default_factory=list)
