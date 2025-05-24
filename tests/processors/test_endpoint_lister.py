from src.processors.swagger.endpoint_lister import EndpointLister
from src.models.api_path import APIPath


def test_list_endpoints_outputs_paths(capsys):
    paths = [
        APIPath(path="/users", yaml=""),
        APIPath(path="/items", yaml=""),
        APIPath(path="/accounts", yaml=""),
    ]
    EndpointLister.list_endpoints(paths)
    captured = capsys.readouterr()
    output = captured.out
    assert "Endpoints that can be used with the --endpoints flag:" in output
    for p in ["/accounts", "/items", "/users"]:
        assert f"- {p}" in output
