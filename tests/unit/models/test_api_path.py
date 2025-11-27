import pytest
from src.models.api_path import APIPath


def test_api_path_instantiation():
    """Test that APIPath instances are created with the correct type value."""
    path = "/test/path"
    yaml_content = "test: content"
    api_path = APIPath(path=path, yaml=yaml_content)

    assert api_path.type == "path"
    assert api_path.path == path
    assert api_path.yaml == yaml_content


@pytest.mark.parametrize(
    "path,prefixes,expected",
    [
        ("/api/pets", None, "/pets"),
        ("/api/pets/123", None, "/pets/123"),
        ("/api/users/profile", None, "/users/profile"),
        ("/api/v1/pets", None, "/v1/pets"),
        ("/api/v2/pets/123", None, "/v2/pets/123"),
        ("/api/v10/pets", None, "/v10/pets"),
        ("api/v1/pets", None, "/v1/pets"),
        ("/api/v1beta/pets", None, "/v1beta/pets"),
        ("/v2/products", None, "/v2/products"),
        ("/pets", None, "/pets"),
        ("/pets", "/custom", "/pets"),
        ("/users/profile", None, "/users/profile"),
        ("/pets?limit=10", None, "/pets?limit=10"),
        ("/api/v1/", None, "/v1"),
        ("/api/v1", None, "/v1"),
        ("/", None, "/"),
        ("", None, ""),
        ("//api//v1//pets", None, "/v1/pets"),
        ("/api/v1/pets/", None, "/v1/pets"),
        ("/public-api/pets", ["/public-api"], "/pets"),
        ("/api/v2beta/pets", ["/api", "/api/v2beta"], "/pets"),
        ("/api", ["/api"], "/"),
        ("/", ["/"], "/"),
        ("", [""], ""),
        ("//api//v1//pets", ["//api//v1"], "/pets"),
        ("/am/api/pets/", ["am/api"], "/pets"),
        ("/am/api/v1/orders", ["/am/api", "/v1"], "/v1/orders"),
    ],
)
def test_normalize_path(path, prefixes, expected):
    normalized_path, _ = APIPath.normalize_path(path, prefixes)
    assert normalized_path == expected


def test_normalize_path_custom_prefixes_extend_api():
    """Test that custom prefixes extend /api instead of replacing it."""
    normalized_path, _ = APIPath.normalize_path("/api/users", ["/beta"])
    assert normalized_path == "/users"


def test_normalize_path_returns_removed_prefix():
    """Test that normalize_path returns both the normalized path and the removed prefix."""
    normalized_path, removed_prefix = APIPath.normalize_path("/api/pets", None)
    assert normalized_path == "/pets"
    assert removed_prefix == "/api"

    normalized_path, removed_prefix = APIPath.normalize_path("/api/v1/users", None)
    assert normalized_path == "/v1/users"
    assert removed_prefix == "/api"

    normalized_path, removed_prefix = APIPath.normalize_path("/public-api/pets", ["/public-api"])
    assert normalized_path == "/pets"
    assert removed_prefix == "/public-api"

    normalized_path, removed_prefix = APIPath.normalize_path("/api/v2beta/pets", ["/api", "/api/v2beta"])
    assert normalized_path == "/pets"
    assert removed_prefix == "/api/v2beta"

    normalized_path, removed_prefix = APIPath.normalize_path("/pets", None)
    assert normalized_path == "/pets"
    assert removed_prefix == ""

    normalized_path, removed_prefix = APIPath.normalize_path("/", None)
    assert normalized_path == "/"
    assert removed_prefix == ""


def test_api_path_to_json():
    """Test that APIPath instances are correctly converted to JSON."""
    path = "/test/path"
    yaml_content = "test: content"
    api_path = APIPath(path=path, yaml=yaml_content)

    json_data = api_path.to_json()
    assert json_data == {
        "path": path,
        "yaml": yaml_content,
        "type": "path",
    }
