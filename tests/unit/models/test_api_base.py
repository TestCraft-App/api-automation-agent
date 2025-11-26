import pytest
from src.models.api_verb import APIBase


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/pets/123", "/pets"),
        ("/users/profile", "/users"),
        ("/pets/123?limit=10", "/pets"),
        ("/users/profile?expand=true", "/users"),
        ("pets/123", "/pets"),
        ("/pets", "/pets"),
        ("pets", "/pets"),
        ("/v1/pets", "/v1/pets"),
        ("/v1/pets/123", "/v1/pets"),
        ("/v2/pets", "/v2/pets"),
        ("/v10/pets", "/v10/pets"),
        ("/v1beta/pets", "/v1beta/pets"),
        ("/v2alpha/pets", "/v2alpha/pets"),
        ("/v1", "/v1"),
        ("/void", "/void"),
        ("/pets?limit=10", "/pets"),  # Now supported - query params are stripped
        ("/users?status=active&role=admin", "/users"),  # Multiple query params
    ],
)
def test_get_root_path(path, expected):
    assert APIBase.get_root_path(path) == expected
