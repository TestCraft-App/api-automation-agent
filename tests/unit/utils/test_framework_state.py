from pathlib import Path

from src.models.api_verb import APIVerb
from src.models.generated_model import GeneratedModel
from src.models.framework_state import FrameworkState


def _create_models():
    return [
        GeneratedModel(path="src/models/requests/UserRequest.ts", summary="UserRequest model"),
        GeneratedModel(path="src/models/services/UserService.ts", summary="UserService service"),
    ]


def test_save_and_load_framework_state(tmp_path: Path):
    state = FrameworkState(framework_root=tmp_path)
    state.update_models(
        path="/users",
        models=_create_models(),
    )

    get_verb = APIVerb(full_path="/users", verb="get", root_path="/users", content="test: content")
    post_verb = APIVerb(full_path="/users", verb="post", root_path="/users", content="test: content")
    state.update_tests(get_verb, ["src/tests/users.spec.ts"])
    state.update_tests(post_verb, [])

    state_file = tmp_path / FrameworkState.STATE_FILENAME
    assert state_file.exists()

    loaded_state = FrameworkState.load(tmp_path)
    endpoint_state = loaded_state.get_endpoint("/users")

    assert endpoint_state is not None
    assert "/users - GET" in endpoint_state.verbs
    assert "/users - POST" in endpoint_state.verbs
    assert len(endpoint_state.models) == 2
    assert endpoint_state.models[0].path.startswith("src/models")
    assert endpoint_state.tests == ["src/tests/users.spec.ts"]


def test_upsert_preserves_existing_tests_when_not_provided(tmp_path: Path):
    state = FrameworkState()
    state.update_models(
        path="/orders",
        models=_create_models(),
        auto_save=False,
    )

    # Add tests for GET verb
    get_verb = APIVerb(full_path="/orders", verb="get", root_path="/orders", content="test: content")
    state.update_tests(get_verb, ["src/tests/orders.spec.ts"], auto_save=False)

    # Second update_models call should preserve existing tests
    state.update_models(
        path="/orders",
        models=_create_models(),
        auto_save=False,
    )

    # Add PUT verb
    put_verb = APIVerb(full_path="/orders", verb="put", root_path="/orders", content="test: content")
    state.update_tests(put_verb, [], auto_save=False)

    endpoint_state = state.get_endpoint("/orders")
    assert endpoint_state is not None
    assert "/orders - GET" in endpoint_state.verbs
    assert "/orders - PUT" in endpoint_state.verbs
    assert endpoint_state.tests == ["src/tests/orders.spec.ts"]


def test_update_tests_adds_entry_when_missing(tmp_path: Path):
    state = FrameworkState()
    verb = APIVerb(full_path="/inventory", verb="get", root_path="/inventory", content="test: content")
    state.update_tests(verb, ["src/tests/inventory.spec.ts"], auto_save=False)

    endpoint_state = state.get_endpoint("/inventory")
    assert endpoint_state is not None
    assert endpoint_state.tests == ["src/tests/inventory.spec.ts"]
    assert endpoint_state.models == []


def test_update_tests_merges_with_existing_tests():
    state = FrameworkState()
    state.update_models(
        path="/products",
        models=_create_models(),
        auto_save=False,
    )

    # Add initial test for GET
    get_verb = APIVerb(full_path="/products", verb="get", root_path="/products", content="test: content")
    state.update_tests(get_verb, ["src/tests/products-get.spec.ts"], auto_save=False)

    # Add more tests for POST (should merge with existing)
    post_verb = APIVerb(full_path="/products", verb="post", root_path="/products", content="test: content")
    state.update_tests(
        post_verb, ["src/tests/products-post.spec.ts", "src/tests/products-get.spec.ts"], auto_save=False
    )

    endpoint_state = state.get_endpoint("/products")
    assert endpoint_state is not None
    assert endpoint_state.tests == ["src/tests/products-get.spec.ts", "src/tests/products-post.spec.ts"]


def test_load_ignores_invalid_json(tmp_path: Path):
    state_file = tmp_path / FrameworkState.STATE_FILENAME
    state_file.write_text("{invalid json", encoding="utf-8")

    loaded_state = FrameworkState.load(tmp_path)
    assert loaded_state.generated_endpoints == {}


def test_model_metadata_to_dict_with_summary():
    from src.models.framework_state import ModelMetadata

    metadata = ModelMetadata(path="test.ts", summary="Test model")
    result = metadata.to_dict()
    assert result == {"path": "test.ts", "summary": "Test model"}


def test_model_metadata_to_dict_without_summary():
    from src.models.framework_state import ModelMetadata

    metadata = ModelMetadata(path="test.ts", summary="")
    result = metadata.to_dict()
    assert result == {"path": "test.ts"}


def test_model_metadata_from_dict_with_summary():
    from src.models.framework_state import ModelMetadata

    data = {"path": "test.ts", "summary": "Test model"}
    metadata = ModelMetadata.from_dict(data)
    assert metadata.path == "test.ts"
    assert metadata.summary == "Test model"


def test_model_metadata_from_dict_without_summary():
    from src.models.framework_state import ModelMetadata

    data = {"path": "test.ts"}
    metadata = ModelMetadata.from_dict(data)
    assert metadata.path == "test.ts"
    assert metadata.summary == ""


def test_model_metadata_from_generated_model():
    from src.models.framework_state import ModelMetadata

    model = GeneratedModel(path="test.ts", fileContent="content", summary="Test")
    metadata = ModelMetadata.from_generated_model(model)
    assert metadata.path == "test.ts"
    assert metadata.summary == "Test"


def test_endpoint_state_to_dict():
    from src.models.framework_state import EndpointState, ModelMetadata

    endpoint = EndpointState(
        path="/users",
        verbs=["/users - GET"],
        models=[ModelMetadata(path="user.ts", summary="User")],
        tests=["test.ts"],
    )
    result = endpoint.to_dict()
    assert result["path"] == "/users"
    assert result["verbs"] == ["/users - GET"]
    assert len(result["models"]) == 1
    assert result["tests"] == ["test.ts"]


def test_endpoint_state_to_dict_empty_lists():
    from src.models.framework_state import EndpointState

    endpoint = EndpointState(path="/users")
    result = endpoint.to_dict()
    assert result["path"] == "/users"
    assert result["verbs"] == []
    assert result["models"] == []
    assert result["tests"] == []


def test_endpoint_state_from_dict():
    from src.models.framework_state import EndpointState

    data = {
        "path": "/users",
        "verbs": ["/users - GET"],
        "models": [{"path": "user.ts", "summary": "User"}],
        "tests": ["test.ts"],
    }
    endpoint = EndpointState.from_dict(data)
    assert endpoint.path == "/users"
    assert endpoint.verbs == ["/users - GET"]
    assert len(endpoint.models) == 1
    assert endpoint.tests == ["test.ts"]


def test_endpoint_state_from_dict_missing_fields():
    from src.models.framework_state import EndpointState

    data = {"path": "/users"}
    endpoint = EndpointState.from_dict(data)
    assert endpoint.path == "/users"
    assert endpoint.verbs == []
    assert endpoint.models == []
    assert endpoint.tests == []


def test_load_with_non_existent_file(tmp_path: Path):
    loaded_state = FrameworkState.load(tmp_path)
    assert loaded_state.generated_endpoints == {}


def test_load_with_invalid_json_structure(tmp_path: Path):
    state_file = tmp_path / FrameworkState.STATE_FILENAME
    state_file.write_text('{"invalid": "structure"}', encoding="utf-8")

    loaded_state = FrameworkState.load(tmp_path)
    assert loaded_state.generated_endpoints == {}


def test_load_with_missing_path_in_entry(tmp_path: Path):
    state_file = tmp_path / FrameworkState.STATE_FILENAME
    state_file.write_text(
        '{"generated_endpoints": [{"verbs": ["GET"], "models": []}]}',
        encoding="utf-8",
    )

    loaded_state = FrameworkState.load(tmp_path)
    # Entry without path should be filtered out
    assert loaded_state.generated_endpoints == {}


def test_save_creates_directory(tmp_path: Path):
    subdir = tmp_path / "subdir"
    state = FrameworkState(framework_root=subdir)
    state.update_models(path="/test", models=[], auto_save=True)
    state_file = subdir / FrameworkState.STATE_FILENAME
    assert state_file.exists()
    assert subdir.exists()


def test_are_models_generated_for_path():
    state = FrameworkState()
    assert state.are_models_generated_for_path("/users") is False

    state.update_models(path="/users", models=_create_models(), auto_save=False)
    assert state.are_models_generated_for_path("/users") is True
    assert state.are_models_generated_for_path("/orders") is False


def test_are_tests_generated_for_verb_non_existent_endpoint():
    state = FrameworkState()
    verb = APIVerb(full_path="/users", verb="get", root_path="/users", content="test: content")
    assert state.are_tests_generated_for_verb(verb) is False


def test_are_tests_generated_for_verb_non_existent_verb():
    state = FrameworkState()
    state.update_models(path="/users", models=_create_models(), auto_save=False)
    verb = APIVerb(full_path="/users", verb="get", root_path="/users", content="test: content")
    assert state.are_tests_generated_for_verb(verb) is False

    # Add a different verb
    post_verb = APIVerb(full_path="/users", verb="post", root_path="/users", content="test: content")
    state.update_tests(post_verb, ["test.ts"], auto_save=False)
    assert state.are_tests_generated_for_verb(verb) is False
    assert state.are_tests_generated_for_verb(post_verb) is True


def test_update_models_creates_new_endpoint():
    state = FrameworkState()
    assert "/users" not in state.generated_endpoints

    state.update_models(path="/users", models=_create_models(), auto_save=False)
    assert "/users" in state.generated_endpoints
    endpoint = state.get_endpoint("/users")
    assert endpoint is not None
    assert len(endpoint.models) == 2


def test_update_models_updates_existing_endpoint():
    state = FrameworkState()
    initial_models = [GeneratedModel(path="old.ts", summary="Old")]
    state.update_models(path="/users", models=initial_models, auto_save=False)

    new_models = _create_models()
    state.update_models(path="/users", models=new_models, auto_save=False)

    endpoint = state.get_endpoint("/users")
    assert len(endpoint.models) == 2
    assert endpoint.models[0].path == new_models[0].path


def test_update_tests_creates_new_endpoint_if_needed():
    state = FrameworkState()
    assert "/users" not in state.generated_endpoints

    verb = APIVerb(full_path="/users", verb="get", root_path="/users", content="test: content")
    state.update_tests(verb, ["test.ts"], auto_save=False)

    assert "/users" in state.generated_endpoints
    endpoint = state.get_endpoint("/users")
    assert endpoint is not None
    assert "/users - GET" in endpoint.verbs


def test_update_tests_deduplicates_tests():
    state = FrameworkState()
    verb1 = APIVerb(full_path="/users", verb="get", root_path="/users", content="test: content")
    verb2 = APIVerb(full_path="/users", verb="post", root_path="/users", content="test: content")

    state.update_tests(verb1, ["test1.ts", "test2.ts"], auto_save=False)
    state.update_tests(verb2, ["test2.ts", "test3.ts"], auto_save=False)

    endpoint = state.get_endpoint("/users")
    # Should be sorted and deduplicated
    assert endpoint.tests == ["test1.ts", "test2.ts", "test3.ts"]


def test_get_endpoint_returns_none():
    state = FrameworkState()
    assert state.get_endpoint("/non-existent") is None


def test_get_endpoint_returns_correct_state():
    state = FrameworkState()
    state.update_models(path="/users", models=_create_models(), auto_save=False)

    endpoint = state.get_endpoint("/users")
    assert endpoint is not None
    assert endpoint.path == "/users"
    assert len(endpoint.models) == 2
