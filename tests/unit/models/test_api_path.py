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
        ("/api/pets/123", None,"/pets/123"),
        ("/api/users/profile", None, "/users/profile"),
        ("/api/v1/pets", None, "/v1/pets"),
        ("/api/v2/pets/123", None, "/v2/pets/123"),
        ("/api/v10/pets", None, "/v10/pets"),
        ("api/v1/pets", None, "/v1/pets"),
        ("/api/v1beta/pets", None, "/v1beta/pets"),
        ("/v2/products", None, "/v2/products"),
        ("/pets", None, "/pets"),
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
    assert APIPath.normalize_path(path, prefixes) == expected


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
