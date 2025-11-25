from pathlib import Path

from src.models.api_verb import APIVerb
from src.models.generated_model import GeneratedModel
from src.utils.framework_state import FrameworkState


def _create_models():
    return [
        GeneratedModel(path="src/models/requests/UserRequest.ts", summary="UserRequest model"),
        GeneratedModel(path="src/models/services/UserService.ts", summary="UserService service"),
    ]


def test_save_and_load_framework_state(tmp_path: Path):
    state = FrameworkState()
    state.update_models(
        path="/users",
        models=_create_models(),
    )

    get_verb = APIVerb(path="/users", verb="get", root_path="/users", yaml={})
    post_verb = APIVerb(path="/users", verb="post", root_path="/users", yaml={})
    state.update_tests(get_verb, ["src/tests/users.spec.ts"])
    state.update_tests(post_verb, [])

    state_file = state.save(tmp_path)
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
    )

    # Add tests for GET verb
    get_verb = APIVerb(path="/orders", verb="get", root_path="/orders", yaml={})
    state.update_tests(get_verb, ["src/tests/orders.spec.ts"])

    # Second update_models call should preserve existing tests
    state.update_models(
        path="/orders",
        models=_create_models(),
    )

    # Add PUT verb
    put_verb = APIVerb(path="/orders", verb="put", root_path="/orders", yaml={})
    state.update_tests(put_verb, [])

    endpoint_state = state.get_endpoint("/orders")
    assert endpoint_state is not None
    assert "/orders - GET" in endpoint_state.verbs
    assert "/orders - PUT" in endpoint_state.verbs
    assert endpoint_state.tests == ["src/tests/orders.spec.ts"]


def test_update_tests_adds_entry_when_missing(tmp_path: Path):
    state = FrameworkState()
    verb = APIVerb(path="/inventory", verb="get", root_path="/inventory", yaml={})
    state.update_tests(verb, ["src/tests/inventory.spec.ts"])

    endpoint_state = state.get_endpoint("/inventory")
    assert endpoint_state is not None
    assert endpoint_state.tests == ["src/tests/inventory.spec.ts"]
    assert endpoint_state.models == []


def test_update_tests_merges_with_existing_tests():
    state = FrameworkState()
    state.update_models(
        path="/products",
        models=_create_models(),
    )

    # Add initial test for GET
    get_verb = APIVerb(path="/products", verb="get", root_path="/products", yaml={})
    state.update_tests(get_verb, ["src/tests/products-get.spec.ts"])

    # Add more tests for POST (should merge with existing)
    post_verb = APIVerb(path="/products", verb="post", root_path="/products", yaml={})
    state.update_tests(post_verb, ["src/tests/products-post.spec.ts", "src/tests/products-get.spec.ts"])

    endpoint_state = state.get_endpoint("/products")
    assert endpoint_state is not None
    assert endpoint_state.tests == ["src/tests/products-get.spec.ts", "src/tests/products-post.spec.ts"]


def test_load_ignores_invalid_json(tmp_path: Path):
    state_file = tmp_path / FrameworkState.STATE_FILENAME
    state_file.write_text("{invalid json", encoding="utf-8")

    loaded_state = FrameworkState.load(tmp_path)
    assert loaded_state.generated_endpoints == {}
