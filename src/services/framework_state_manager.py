"""Service for managing framework state persistence and endpoint generation decisions."""

from pathlib import Path
from typing import Dict, List

from src.models.api_verb import APIVerb

from ..configuration.config import Config
from ..models import GeneratedModel, ModelInfo
from ..services.file_service import FileService
from ..utils.framework_state import FrameworkState
from ..utils.logger import Logger


class FrameworkStateManager:
    """Manages framework state persistence and loading for incremental generation."""

    def __init__(self, config: Config, file_service: FileService):
        """
        Initialize the FrameworkStateManager.

        Args:
            config: Configuration instance
            file_service: FileService instance for reading model files
        """
        self.config = config
        self.file_service = file_service
        self.logger = Logger.get_logger(__name__)
        self._framework_state = FrameworkState()
        self._state_loaded_models: Dict[str, ModelInfo] = {}

    @property
    def _framework_root(self) -> Path:
        """Get the framework root directory."""
        return Path(self.config.destination_folder)

    def load_state(self):
        """Load framework state from disk and hydrate model metadata."""
        self._framework_state = FrameworkState.load(self._framework_root)
        self._state_loaded_models = self._load_models_from_state()
        if self._framework_state.generated_endpoints:
            endpoint_count = len(self._framework_state.generated_endpoints)
            endpoint_keys = list(self._framework_state.generated_endpoints.keys())
            self.logger.info(
                f"🔁 Loaded framework state with {endpoint_count} endpoint(s): {endpoint_keys}"
            )

    def _load_models_from_state(self) -> Dict[str, ModelInfo]:
        """
        Load existing model file contents guided by the persisted state.

        Returns:
            Dict[str, ModelInfo]: Mapping of endpoint path to ModelInfo for pre-existing models.
        """
        loaded: Dict[str, ModelInfo] = {}
        if not self._framework_state.generated_endpoints:
            return loaded

        for endpoint in self._framework_state.generated_endpoints.values():
            generated_models: List[GeneratedModel] = []
            file_entries: List[str] = []

            for model_meta in endpoint.models:
                model_path = self._framework_root / model_meta.path
                content = self.file_service.read_file(str(model_path))
                if content is None:
                    self.logger.warning(f"⚠️ Unable to load model file from state: {model_meta.path}")
                    continue

                generated_model = GeneratedModel(
                    path=model_meta.path,
                    fileContent=content,
                    summary=model_meta.summary,
                )
                generated_models.append(generated_model)
                file_label = (
                    model_meta.path if not model_meta.summary else f"{model_meta.path} - {model_meta.summary}"
                )
                file_entries.append(file_label)

            if generated_models:
                loaded[endpoint.path] = ModelInfo(
                    path=endpoint.path, files=file_entries, models=generated_models
                )

        if loaded:
            self.logger.info(f"🔁 Loaded {len(loaded)} endpoint(s) from framework state.")

        return loaded

    def get_preloaded_model_info(self) -> List[ModelInfo]:
        """Return previously loaded model info objects."""
        return list(self._state_loaded_models.values())

    def are_models_generated_for_path(self, path_name: str) -> bool:
        """
        Check if models have been generated for a given path.

        Args:
            path_name: The endpoint path to check

        Returns:
            bool: True if models exist for the path, False otherwise
        """
        return self._framework_state.are_models_generated_for_path(path_name)

    def are_tests_generated_for_verb(self, verb: APIVerb) -> bool:
        """
        Check if tests have been generated for a given verb.

        Args:
            verb: The API verb to check

        Returns:
            bool: True if tests exist for the verb, False otherwise
        """
        return self._framework_state.are_tests_generated_for_verb(verb)

    def should_generate_models_for_path(self, path_name: str) -> bool:
        """
        Check if endpoint should be generated, considering override configuration.

        Args:
            path_name: The endpoint path to check

        Returns:
            bool: True if endpoint should be generated, False otherwise
        """
        if not self.are_models_generated_for_path(path_name):
            return True

        if self.config.override:
            self.logger.info(f"\n⚠️ Path '{path_name}' already exists. Overriding models.\n")
            return True

        return False

    def should_generate_tests_verb(self, verb: APIVerb) -> bool:
        """
        Check if tests should be generated for a given APIVerb, considering override configuration.

        Args:
            verb: The API verb to check

        Returns:
            bool: True if tests should be generated, False otherwise
        """
        if not self.are_tests_generated_for_verb(verb):
            return True

        if self.config.override:
            self.logger.info(
                f"\n⚠️ Tests for '{verb.path} - {verb.verb.upper()}' already exist. Overriding tests."
            )
            return True

        return False

    def update_models_state(self, path: str, models: List[GeneratedModel]):
        """Update or create endpoint state for models in the framework state."""
        self._framework_state.update_models(path=path, models=models)
        self._framework_state.save(self._framework_root)

    def update_tests_state(self, verb: APIVerb, tests: List[str]):
        """Update tests for an endpoint in the framework state."""
        self._framework_state.update_tests(verb, tests)
        self._framework_state.save(self._framework_root)

    def get_endpoint_state(self, path: str):
        """
        Get the endpoint state for a given path.

        Args:
            path: The endpoint path to retrieve

        Returns:
            EndpointState if found, None otherwise
        """
        return self._framework_state.get_endpoint(path)

    def get_endpoint_count(self) -> int:
        """
        Get the count of generated endpoints in the state.

        Returns:
            int: Number of endpoints in the state
        """
        return len(self._framework_state.generated_endpoints)
