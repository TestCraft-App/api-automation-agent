from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from src.models.api_verb import APIVerb

from .generated_model import GeneratedModel
from ..utils.logger import Logger


@dataclass
class ModelMetadata:
    """Lightweight representation of a generated model stored in state."""

    path: str
    summary: str = ""

    def to_dict(self) -> Dict[str, str]:
        data = {"path": self.path}
        if self.summary:
            data["summary"] = self.summary
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "ModelMetadata":
        return cls(path=data["path"], summary=data.get("summary", ""))

    @classmethod
    def from_generated_model(cls, model: GeneratedModel) -> "ModelMetadata":
        return cls(path=model.path, summary=model.summary)


@dataclass
class EndpointState:
    """Metadata stored for a generated endpoint (path)."""

    path: str
    verbs: List[str] = field(default_factory=list)
    models: List[ModelMetadata] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "path": self.path,
            "verbs": self.verbs,
            "models": [model.to_dict() for model in self.models],
            "tests": self.tests,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "EndpointState":
        model_dicts = data.get("models", [])
        models = [ModelMetadata.from_dict(model) for model in model_dicts]
        return cls(
            path=data["path"],
            verbs=list(data.get("verbs", [])),
            models=models,
            tests=list(data.get("tests", [])),
        )


@dataclass
class FrameworkState:
    """
    Persistence layer for the automation framework state.

    Tracks generated endpoints plus the models/tests produced for each path.
    """

    generated_endpoints: Dict[str, EndpointState] = field(default_factory=dict)
    framework_root: Optional[Path] = None
    logger: Logger = field(default_factory=lambda: Logger.get_logger(__name__), repr=False)

    STATE_FILENAME = "framework-state.json"

    @classmethod
    def load(cls, framework_root: Path) -> "FrameworkState":
        state_file = framework_root / cls.STATE_FILENAME
        if not state_file.exists():
            return cls(framework_root=framework_root)

        try:
            raw_state = json.loads(state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            Logger.get_logger(__name__).warning(f"⚠️ Invalid framework state file: {exc}")
            return cls(framework_root=framework_root)

        entries = raw_state.get("generated_endpoints", [])
        endpoints = {entry["path"]: EndpointState.from_dict(entry) for entry in entries if "path" in entry}
        return cls(generated_endpoints=endpoints, framework_root=framework_root)

    def save(self) -> Path:
        self.framework_root.mkdir(parents=True, exist_ok=True)
        state_file = self.framework_root / self.STATE_FILENAME
        serialized_state = {
            "generated_endpoints": [endpoint.to_dict() for endpoint in self.generated_endpoints.values()]
        }
        state_file.write_text(json.dumps(serialized_state, indent=2), encoding="utf-8")
        return state_file

    def are_models_generated_for_path(self, path: str) -> bool:
        return path in self.generated_endpoints

    def are_tests_generated_for_verb(self, verb: APIVerb) -> bool:
        endpoint = self.generated_endpoints.get(verb.root_path)
        if not endpoint:
            return False
        return f"{verb.path} - {verb.verb.upper()}" in endpoint.verbs

    def update_models(
        self,
        path: str,
        models: Iterable[GeneratedModel],
        auto_save: bool = True,
        framework_root: Optional[Path] = None,
    ) -> EndpointState:
        model_metadata = [ModelMetadata.from_generated_model(model) for model in models]

        endpoint_state = self.generated_endpoints.get(path)
        if endpoint_state:
            endpoint_state.models = model_metadata
        else:
            endpoint_state = EndpointState(path=path, models=model_metadata)
            self.generated_endpoints[path] = endpoint_state

        if auto_save:
            self.save()

        return endpoint_state

    def update_tests(
        self,
        verb: APIVerb,
        tests: Iterable[str],
        auto_save: bool = True,
        framework_root: Optional[Path] = None,
    ) -> EndpointState:
        endpoint = self.generated_endpoints.get(verb.root_path)
        if not endpoint:
            endpoint = EndpointState(path=verb.root_path)
            self.generated_endpoints[verb.root_path] = endpoint

        verb_key = f"{verb.path} - {verb.verb.upper()}"
        if verb_key not in endpoint.verbs:
            endpoint.verbs.append(verb_key)

        all_tests = list(endpoint.tests) + list(tests)
        endpoint.tests = sorted(set(all_tests))

        if auto_save:
            self.save()

        return endpoint

    def get_endpoint(self, path: str) -> Optional[EndpointState]:
        return self.generated_endpoints.get(path)
