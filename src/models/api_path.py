from dataclasses import dataclass, field
from typing import List, Optional
from .api_base import APIBase


@dataclass
class APIPath(APIBase):
    """Represents an API path with its metadata"""

    type: str = field(default="path", init=False)

    @staticmethod
    def normalize_path(path: str, prefixes: Optional[List[str]] = None) -> str:
        """Normalizes the path by removing api and prefixes."""

        def _format_path(s: str) -> str:
            parts = [p for p in s.split("/") if p]
            return "/" + "/".join(parts) if parts else ""

        def _starts_with_prefix(path: str, prefix: str) -> bool:
            if not path.startswith(prefix):
                return False
            if len(path) == len(prefix):
                return True
            return path[len(prefix)] == "/"

        normalized_path = _format_path(path)
        if not normalized_path:
            return path

        default_prefixes = ["/api"]
        if prefixes:
            all_prefixes = default_prefixes + [p for p in prefixes if p not in default_prefixes]
        else:
            all_prefixes = default_prefixes

        normalized_prefixes = []
        for pre in all_prefixes:
            normalized_prefixes.append(_format_path(pre))

        normalized_prefixes.sort(key=len, reverse=True)
        for prefix in normalized_prefixes:
            if _starts_with_prefix(normalized_path, prefix):
                return normalized_path[len(prefix) :] or "/"

        return normalized_path
