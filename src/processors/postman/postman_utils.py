import json
import re
from typing import Any, Dict, Iterable, List
from urllib.parse import parse_qsl

from ...models import APIDefinition
from ...processors.postman.models import RequestData, VerbInfo


class PostmanUtils:
    """
    All pure‐logic for parsing Postman JSON → RequestData, VerbInfo, ServiceVerbs.
    """

    numeric_only = r"^\d+$"

    @staticmethod
    def extract_requests(data: Any, path: str = "") -> List[RequestData]:
        results: List[RequestData] = []

        def _walk(item: Any, cur: str):
            if isinstance(item, dict):
                if "item" in item and isinstance(item["item"], list):
                    new_path = f"{cur}/{PostmanUtils.to_camel_case(item['name'])}" if "name" in item else cur
                    for sub in item["item"]:
                        _walk(sub, new_path)
                elif PostmanUtils.item_is_a_test_case(item):
                    rd = PostmanUtils.extract_request_data(item, cur)
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
    def extract_request_data(data: Dict[str, Any], current_path: str) -> RequestData:
        req = data.get("request", {})
        verb = req.get("method", "")
        raw_url = req.get("url")
        if isinstance(raw_url, dict):
            path = raw_url.get("raw", "")
        else:
            path = raw_url or ""

        # body
        raw_body = req.get("body", {}).get("raw", "").replace("\r", "").replace("\n", "")
        try:
            body = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            body = {}

        # scripts
        prereq: List[str] = []
        script: List[str] = []
        for ev in data.get("event", []):
            if ev.get("listen") == "prerequest":
                prereq = ev.get("script", {}).get("exec", [])
            elif ev.get("listen") == "test":
                script = ev.get("script", {}).get("exec", [])

        # name & file_path
        name = PostmanUtils.to_camel_case(data.get("name", ""))
        file_path = f"src/tests{current_path}/{name}"

        return RequestData(
            service="",
            file_path=file_path,
            path=path,
            verb=verb,
            body=body,
            prerequest=prereq,
            script=script,
            name=name,
        )

    @staticmethod
    def extract_verb_path_info(requests: List[RequestData]) -> List[VerbInfo]:
        distinct = {item.path.split("?")[0] for item in requests}
        out: List[VerbInfo] = []

        for base in distinct:
            matches = [r for r in requests if r.path.startswith(base)]
            verbs = {r.verb for r in matches}
            for v in verbs:
                qp: Dict[str, str] = {}
                body_attrs: Dict[str, Any] = {}
                for m in matches:
                    if m.verb != v:
                        continue
                    # body
                    PostmanUtils._accumulate_request_body_attributes(body_attrs, m.body)
                    # query
                    parts = m.path.split("?", 1)
                    if len(parts) == 2 and parts[1]:
                        PostmanUtils.accumulate_query_params(qp, parts[1])
                out.append(
                    VerbInfo(
                        verb=v,
                        root_path=PostmanUtils.get_root_path(base),
                        path=base,
                        query_params=qp,
                        body_attributes=body_attrs,
                    )
                )
        return out

    @staticmethod
    def map_verb_path_pairs_to_services(
        verb_path_pairs: List[RequestData], no_query_params_routes_grouped_by_service: Dict[str, List[str]]
    ) -> Dict[str, List[VerbInfo]]:
        # first group raw paths by service root
        verb_chunks_with_query_params = PostmanUtils.extract_verb_path_info(verb_path_pairs)

        verb_path_pairs_and_services: Dict[str, List[VerbInfo]] = {}
        for verb_path_pair in verb_chunks_with_query_params:
            for service, routes in no_query_params_routes_grouped_by_service.items():
                if verb_path_pair.path in routes:
                    if service not in verb_path_pairs_and_services:
                        verb_path_pairs_and_services[service] = []

                    verb_path_pairs_and_services[service].append(
                        VerbInfo(
                            verb=verb_path_pair.verb,
                            path=verb_path_pair.path,
                            query_params=verb_path_pair.query_params,
                            body_attributes=verb_path_pair.body_attributes,
                            root_path="",
                        )
                    )
        return verb_path_pairs_and_services

    @staticmethod
    def group_paths_by_service(paths: Iterable[str]) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for p in paths:
            segs = p.split("/", 2)
            svc = segs[1] if len(segs) > 1 else ""
            out.setdefault(svc, []).append(p)
        return out

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
    def extract_env_vars(requests: APIDefinition) -> List[str]:
        evs = set()
        for r in requests.definitions:
            if r.path.startswith("{{"):
                m = re.match(r"\{\{(.*?)}}", r.path)
                if m:
                    evs.add(m.group(1))
                    break
        return list(evs)

    @staticmethod
    def get_root_path(full_path: str) -> str:
        segs = full_path.strip("/").split("/", 1)
        return segs[0] if len(segs) > 1 else ""

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
