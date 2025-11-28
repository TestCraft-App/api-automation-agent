from dataclasses import dataclass
from typing import Any, Dict, List


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
