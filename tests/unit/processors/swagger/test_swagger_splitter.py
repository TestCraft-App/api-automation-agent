from src.processors.swagger import APIDefinitionSplitter
from src.models import APIPath, APIVerb
import yaml


def test_splitter_basic():
    spec = {
        "paths": {
            "/api/v1/users": {
                "get": {"responses": {"200": {"description": "ok"}}},
                "post": {"responses": {"201": {"description": "created"}}},
            }
        }
    }

    splitter = APIDefinitionSplitter()
    base_yaml, parts = splitter.split(spec)

    assert yaml.safe_load(base_yaml) == {}

    assert len(parts) == 3
    assert sum(isinstance(p, APIPath) for p in parts) == 1
    assert sum(isinstance(p, APIVerb) for p in parts) == 2
    assert parts[0].full_path == "/v1/users"
    assert parts[0].type == "path"
    assert parts[1].full_path == "/v1/users"
    assert parts[1].type == "verb"
    assert parts[1].verb == "GET"
    assert parts[2].full_path == "/v1/users"
    assert parts[2].type == "verb"
    assert parts[2].verb == "POST"


def test_splitter_on_populated_openapi_spec():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Title", "version": "1.0.0", "description": "Description"},
        "servers": [{"url": "http://localhost:3000", "description": "Local server"}],
        "paths": {
            "/api/v1/users": {
                "get": {"responses": {"200": {"description": "ok"}}},
                "post": {"responses": {"201": {"description": "created"}}},
            }
        },
    }

    splitter = APIDefinitionSplitter()
    base_yaml, parts = splitter.split(spec)

    assert len(parts) == 3
    assert sum(isinstance(p, APIPath) for p in parts) == 1
    assert sum(isinstance(p, APIVerb) for p in parts) == 2

    assert "/api/v1/users" not in base_yaml
    base_yaml_dict = yaml.safe_load(base_yaml)
    assert base_yaml_dict["openapi"] == "3.0.0"
    assert base_yaml_dict["info"]["title"] == "Title"
    assert base_yaml_dict["servers"] == [{"url": "http://localhost:3000", "description": "Local server"}]


def test_splitter_empty_paths():
    spec = {"paths": {}}

    splitter = APIDefinitionSplitter()
    _, parts = splitter.split(spec)

    assert len(parts) == 0


def test_splitter_no_paths_key():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Title", "version": "1.0.0", "description": "Description"},
    }

    splitter = APIDefinitionSplitter()
    _, parts = splitter.split(spec)

    assert len(parts) == 0


def test_splitter_path_with_no_verbs():
    spec = {"paths": {"/api/v1/items": {}}}

    splitter = APIDefinitionSplitter()
    _, parts = splitter.split(spec)

    assert len(parts) == 1
    assert isinstance(parts[0], APIPath)
    assert parts[0].full_path == "/v1/items"


def test_splitter_path_normalization():
    spec = {"paths": {"/api/v1/widgets/": {"get": {"responses": {"200": {"description": "ok"}}}}}}

    splitter = APIDefinitionSplitter()
    _, parts = splitter.split(spec)

    assert len(parts) == 2
    assert isinstance(parts[0], APIPath)
    assert parts[0].full_path == "/v1/widgets"
    assert isinstance(parts[1], APIVerb)
    assert parts[1].full_path == "/v1/widgets"
    assert parts[1].verb == "GET"


def test_splitter_path_with_custom_prefixes():
    spec = {"paths": {"/public-api/v1/widgets/": {"get": {"responses": {"200": {"description": "ok"}}}}}}

    splitter = APIDefinitionSplitter()
    _, parts = splitter.split(spec, ["/public-api/v1"])

    assert len(parts) == 2
    assert isinstance(parts[0], APIPath)
    assert parts[0].full_path == "/widgets"
    assert isinstance(parts[1], APIVerb)
    assert parts[1].full_path == "/widgets"
    assert parts[1].verb == "GET"


def test_splitter_path_with_parameters():
    spec = {
        "paths": {
            "/api/v1/users/{user_id}": {
                "get": {"responses": {"200": {"description": "ok"}}},
                "put": {"responses": {"200": {"description": "updated"}}},
            }
        }
    }

    splitter = APIDefinitionSplitter()
    _, parts = splitter.split(spec)

    assert len(parts) == 3
    assert parts[0].full_path == "/v1/users/{user_id}"
    assert parts[1].full_path == "/v1/users/{user_id}"
    assert parts[1].verb == "GET"
    assert parts[2].full_path == "/v1/users/{user_id}"
    assert parts[2].verb == "PUT"


def test_splitter_multiple_paths():
    spec = {
        "paths": {
            "/api/v1/first": {"get": {"responses": {"200": {"description": "ok"}}}},
            "/api/v1/second/path": {"post": {"responses": {"201": {"description": "created"}}}},
        }
    }

    splitter = APIDefinitionSplitter()
    _, parts = splitter.split(spec)

    assert len(parts) == 4
    path_objects = [p for p in parts if isinstance(p, APIPath)]
    verb_objects = [p for p in parts if isinstance(p, APIVerb)]

    assert len(path_objects) == 2
    assert len(verb_objects) == 2

    assert path_objects[0].full_path == "/v1/first"
    assert verb_objects[0].full_path == "/v1/first"
    assert verb_objects[0].verb == "GET"

    assert path_objects[1].full_path == "/v1/second/path"
    assert verb_objects[1].full_path == "/v1/second/path"
    assert verb_objects[1].verb == "POST"


def test_splitter_yaml_output_correctness():
    original_spec = {
        "swagger": "2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {
            "/api/data": {
                "get": {"summary": "Get data", "responses": {"200": {"description": "Success"}}},
                "post": {"summary": "Create data", "responses": {"201": {"description": "Created"}}},
            }
        },
    }

    splitter = APIDefinitionSplitter()
    _, parts = splitter.split(original_spec)

    assert len(parts) == 3

    api_path_obj = next(p for p in parts if isinstance(p, APIPath) and p.full_path == "/data")
    get_verb_obj = next(
        p for p in parts if isinstance(p, APIVerb) and p.full_path == "/data" and p.verb == "GET"
    )
    post_verb_obj = next(
        p for p in parts if isinstance(p, APIVerb) and p.full_path == "/data" and p.verb == "POST"
    )

    expected_path_yaml = {
        "/api/data": {
            "get": {
                "summary": "Get data",
                "responses": {"200": {"description": "Success"}},
            },
            "post": {
                "summary": "Create data",
                "responses": {"201": {"description": "Created"}},
            },
        }
    }
    assert yaml.safe_load(api_path_obj.content) == expected_path_yaml

    expected_get_verb_yaml = {
        "/api/data": {
            "get": {
                "summary": "Get data",
                "responses": {"200": {"description": "Success"}},
            }
        }
    }
    assert yaml.safe_load(get_verb_obj.content) == expected_get_verb_yaml

    expected_post_verb_yaml = {
        "/api/data": {
            "post": {
                "summary": "Create data",
                "responses": {"201": {"description": "Created"}},
            }
        }
    }
    assert yaml.safe_load(post_verb_obj.content) == expected_post_verb_yaml


def test_splitter_verb_root_path():
    spec = {
        "paths": {
            "/api/v1/items/{item_id}/details": {
                "get": {"responses": {"200": {"description": "ok"}}},
                "put": {"responses": {"200": {"description": "updated"}}},
            }
        }
    }

    splitter = APIDefinitionSplitter()
    _, parts = splitter.split(spec)

    verb_objects = [p for p in parts if isinstance(p, APIVerb)]

    for verb_obj in verb_objects:
        assert verb_obj.full_path == "/v1/items/{item_id}/details"
        assert verb_obj.root_path == "/v1/items"
