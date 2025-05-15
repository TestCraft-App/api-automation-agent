from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RequestData:
    """
    Represents one Postman request/test‐case with its metadata.
    """

    file_path: str
    path: str
    verb: str
    body: Dict[str, Any]
    prerequest: List[str]
    script: List[str]
    name: str


@dataclass
class VerbInfo:
    """
    One (path, verb) combination with all its aggregated query‐params and body attributes.
    """

    verb: str
    root_path: str
    path: str
    query_params: Dict[str, str]
    body_attributes: Dict[str, Any]


@dataclass
class ServiceVerbs:
    """
    A collection of VerbInfo objects belonging to the same service root.
    """

    service: str
    verbs: List[VerbInfo] = field(default_factory=list)
