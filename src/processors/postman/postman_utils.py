import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl

from src.models.api_path import APIPath
from src.models.api_verb import APIVerb

from ...processors.postman.models import RequestData, VerbInfo


class PostmanUtils:
    """
    All pure‐logic for parsing Postman JSON → RequestData, VerbInfo.
    """

    numeric_only = r"^\d+$"

    @staticmethod
    def extract_variables(data: Any) -> List[Dict[str, str]]:
        """Extract variables from Postman data"""
        variables = []
        if isinstance(data, dict) and "variable" in data:
            for var in data["variable"]:
                if isinstance(var, dict) and "key" in var and "value" in var:
                    variables.append({"key": var["key"], "value": var["value"]})
        return variables

    @staticmethod
    def extract_requests(
        data: Any, path: str = "", prefixes: Optional[List[str]] = None
    ) -> List[RequestData]:
        results: List[RequestData] = []

        def _walk(item: Any, cur: str):
            if isinstance(item, dict):
                if "item" in item and isinstance(item["item"], list):
                    new_path = f"{cur}/{PostmanUtils.to_camel_case(item['name'])}" if "name" in item else cur
                    for sub in item["item"]:
                        _walk(sub, new_path)
                elif PostmanUtils.item_is_a_test_case(item):
                    rd = PostmanUtils.extract_request_data(item, cur, prefixes=prefixes)
                    if rd.name not in {r.name for r in results}:
                        results.append(rd)
                else:
                    for v in item.values():
                        _walk(v, cur)
            elif isinstance(item, list):
                for sub in item:
                    _walk(sub, cur)

        _walk(data, path)
        return results

    @staticmethod
    def extract_request_data(
        data: Dict[str, Any], current_path: str, prefixes: Optional[List[str]] = None
    ) -> RequestData:
        req = data.get("request", {})
        verb = req.get("method", "")
        raw_url = req.get("url")
        if isinstance(raw_url, dict):
            # Prefer "raw" as it includes query parameters
            if "raw" in raw_url:
                path = raw_url.get("raw", "")
            elif "path" in raw_url and isinstance(raw_url["path"], list):
                # Reconstruct path from path array and query array
                path = "/" + "/".join(raw_url["path"])
                # Add query parameters if present
                if "query" in raw_url and isinstance(raw_url["query"], list):
                    query_parts = []
                    for q in raw_url["query"]:
                        if isinstance(q, dict) and "key" in q:
                            key = q.get("key", "")
                            value = q.get("value", "")
                            if key:
                                query_parts.append(f"{key}={value}" if value else key)
                    if query_parts:
                        path += "?" + "&".join(query_parts)
            else:
                path = raw_url.get("raw", "")
        else:
            path = raw_url or ""

        # Strip Postman variables like {{BASEURL}} from the path
        path = re.sub(r"\{\{[^}]+\}\}", "", path)

        raw_body = req.get("body", {}).get("raw", "").replace("\r", "").replace("\n", "")
        try:
            body = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            body = {}

        prereq: List[str] = []
        script: List[str] = []
        for ev in data.get("event", []):
            if ev.get("listen") == "prerequest":
                prereq = ev.get("script", {}).get("exec", [])
            elif ev.get("listen") == "test":
                script = ev.get("script", {}).get("exec", [])

        name = PostmanUtils.to_camel_case(data.get("name", ""))
        file_path = f"src/tests{current_path}/{name}"

        normalized_path, prefix = APIPath.normalize_path(path, prefixes)
        service = APIVerb.get_root_path(normalized_path)

        return RequestData(
            service=service,
            file_path=file_path,
            prefix=prefix,
            path=normalized_path,
            verb=verb,
            body=body,
            prerequest=prereq,
            script=script,
            name=name,
        )

    @staticmethod
    def extract_verb_path_info(requests: List[RequestData]) -> List[VerbInfo]:
        """Group requests by base path (without query params) and verb, then aggregate attributes."""
        grouped: Dict[tuple[str, str], List[RequestData]] = {}
        for request in requests:
            base_path = request.path.split("?")[0]
            key = (base_path, request.verb)
            grouped.setdefault(key, []).append(request)

        out: List[VerbInfo] = []
        for (base_path, verb), matches in grouped.items():
            qp: Dict[str, str] = {}
            body_attrs: Dict[str, Any] = {}
            scripts: List[str] = []

            for match in matches:
                PostmanUtils._accumulate_request_body_attributes(body_attrs, match.body)
                parts = match.path.split("?", 1)
                if len(parts) == 2 and parts[1]:
                    PostmanUtils.accumulate_query_params(qp, parts[1])
                scripts.extend(match.script)

            out.append(
                VerbInfo(
                    verb=verb,
                    root_path=requests[0].prefix + APIVerb.get_root_path(base_path),
                    path=base_path,
                    query_params=qp,
                    body_attributes=body_attrs,
                    script=scripts,
                )
            )
        return out

    @staticmethod
    def group_request_data_by_service(requests: List[RequestData]) -> Dict[str, List[RequestData]]:
        """Group RequestData objects by their service."""
        requests_by_service: Dict[str, List[RequestData]] = {}
        for request in requests:
            requests_by_service.setdefault(request.service, []).append(request)
        return requests_by_service

    @staticmethod
    def accumulate_query_params(all_params: Dict[str, str], qs: str) -> None:
        for name, val in parse_qsl(qs, keep_blank_values=True):
            if not name:
                continue
            is_num = bool(re.fullmatch(PostmanUtils.numeric_only, val))
            typ = "number" if is_num else "string"
            prev = all_params.get(name)
            if prev is None or (prev == "number" and typ == "string"):
                all_params[name] = typ

    @staticmethod
    def item_is_a_test_case(item: Any) -> bool:
        if isinstance(item, dict):
            if "request" in item:
                return True
            ev = item.get("event")
            return isinstance(ev, list) and any("request" in e for e in ev)
        return False

    @staticmethod
    def to_camel_case(s: str) -> str:
        parts = [p for p in re.split(r"[^A-Za-z0-9]+", s) if p]
        if not parts:
            return ""
        return parts[0].lower() + "".join(p.title() for p in parts[1:])

    @staticmethod
    def _accumulate_request_body_attributes(all_attrs: Dict[str, Any], body: Dict[str, Any]) -> None:
        for k, v in body.items():
            if k not in all_attrs:
                if isinstance(v, str) and re.fullmatch(PostmanUtils.numeric_only, v):
                    all_attrs[k] = "number"
                elif isinstance(v, str):
                    all_attrs[k] = "string"
                elif isinstance(v, dict):
                    all_attrs[f"{k}Object"] = PostmanUtils._map_object_attributes(v)
                elif isinstance(v, list):
                    all_attrs[f"{k}Object"] = "array"
            else:
                if isinstance(v, str) and not re.fullmatch(PostmanUtils.numeric_only, v):
                    all_attrs[k] = "string"

    @staticmethod
    def _map_object_attributes(obj: Dict[str, Any]) -> Dict[str, Any]:
        mapped: Dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(v, str) and re.fullmatch(PostmanUtils.numeric_only, v):
                mapped[k] = "number"
            elif isinstance(v, str):
                mapped[k] = "string"
            elif isinstance(v, dict):
                mapped[f"{k}Object"] = PostmanUtils._map_object_attributes(v)
            elif isinstance(v, list):
                mapped[f"{k}Object"] = "array"
        return mapped
