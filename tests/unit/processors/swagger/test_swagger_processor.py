import yaml
from src.processors.swagger import APIDefinitionSplitter, APIDefinitionMerger, APIComponentsFilter
from src.processors.swagger_processor import SwaggerProcessor
from src.services.file_service import FileService
from src.configuration.config import Config
from src.models import APIPath, APIVerb


def test_swagger_processor_processes_valid_spec():
    processor = SwaggerProcessor(
        file_loader=FileService(),
        splitter=APIDefinitionSplitter(),
        merger=APIDefinitionMerger(),
        components_filter=APIComponentsFilter(),
        file_service=FileService(),
        config=Config(),
    )
    result = processor.process_api_definition("tests/unit/api_definitions/spec.json")
    assert result is not None
    assert len(result.definitions) == 7
    paths = result.get_paths()
    verbs = result.get_verbs()
    assert len(paths) == 3
    assert len(verbs) == 4


def test_swagger_processsor_filters_endpoint_with_one_verb():
    processor = SwaggerProcessor(
        file_loader=FileService(),
        splitter=APIDefinitionSplitter(),
        merger=APIDefinitionMerger(),
        components_filter=APIComponentsFilter(),
        file_service=FileService(),
        config=Config(),
    )
    processor.config.endpoints = ["/items"]
    result = processor.process_api_definition("tests/unit/api_definitions/spec.json")
    paths = result.get_paths()
    verbs = result.get_verbs()
    assert len(paths) == 1
    assert len(verbs) == 1
    assert all(p.path.startswith("/items") for p in paths)
    assert all(v.path.startswith("/items") for v in verbs)


def test_swagger_processsor_filters_endpoint_with_multiple_verbs():
    processor = SwaggerProcessor(
        file_loader=FileService(),
        splitter=APIDefinitionSplitter(),
        merger=APIDefinitionMerger(),
        components_filter=APIComponentsFilter(),
        file_service=FileService(),
        config=Config(),
    )
    processor.config.endpoints = ["/users"]
    result = processor.process_api_definition("tests/unit/api_definitions/spec.json")
    paths = result.get_paths()
    verbs = result.get_verbs()
    assert len(paths) == 1
    assert len(verbs) == 2
    assert all(p.path.startswith("/users") for p in paths)
    assert all(v.path.startswith("/users") for v in verbs)


def test_swagger_processsor_filters_multiple_endpoints():
    processor = SwaggerProcessor(
        file_loader=FileService(),
        splitter=APIDefinitionSplitter(),
        merger=APIDefinitionMerger(),
        components_filter=APIComponentsFilter(),
        file_service=FileService(),
        config=Config(),
    )
    processor.config.endpoints = ["/users", "/items"]
    result = processor.process_api_definition("tests/unit/api_definitions/spec.json")
    paths = result.get_paths()
    verbs = result.get_verbs()
    assert len(paths) == 2
    assert len(verbs) == 3
    assert all(p.path.startswith("/users") or p.path.startswith("/items") for p in paths)
    assert all(v.path.startswith("/users") or v.path.startswith("/items") for v in verbs)


def test_swagger_processsor_no_matching_endpoints():
    processor = SwaggerProcessor(
        file_loader=FileService(),
        splitter=APIDefinitionSplitter(),
        merger=APIDefinitionMerger(),
        components_filter=APIComponentsFilter(),
        file_service=FileService(),
        config=Config(),
    )
    processor.config.endpoints = ["/nonexistent"]
    result = processor.process_api_definition("tests/unit/api_definitions/spec.json")
    assert len(result.definitions) == 0


def test_swagger_processor_rebuilds_full_path_definition():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {
            "/api/v1/items": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                            },
                        }
                    }
                }
            }
        },
        "servers": [{"url": "https://api.example.com"}],
        "components": {
            "schemas": {
                "Item": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
                }
            }
        },
    }

    splitter = APIDefinitionSplitter()
    base_yaml, parts = splitter.split(spec)
    merger = APIDefinitionMerger()
    merged = merger.merge(parts)
    components_filter = APIComponentsFilter()

    processor = SwaggerProcessor(
        file_loader=FileService(),
        splitter=splitter,
        merger=merger,
        components_filter=components_filter,
        file_service=FileService(),
        config=Config(),
    )
    processor.base_definition = base_yaml

    api_path = next(p for p in merged if isinstance(p, APIPath))
    full_yaml = processor.get_api_path_content(api_path)
    reconstructed = yaml.safe_load(full_yaml)

    assert "/api/v1/items" not in base_yaml
    assert "/api/v1/items" in reconstructed["paths"]

    assert "https://api.example.com" not in api_path.yaml
    assert reconstructed["openapi"] == "3.0.0"
    assert reconstructed["servers"] == [{"url": "https://api.example.com"}]
    assert reconstructed["components"]["schemas"]["Item"] == {
        "type": "object",
        "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
    }


def test_swagger_processor_rebuilds_full_verb_definition():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {"/api/v1/items": {"get": {"responses": {"200": {"description": "ok"}}}}},
        "servers": [{"url": "https://api.example.com"}],
    }

    splitter = APIDefinitionSplitter()
    base_yaml, parts = splitter.split(spec)
    merger = APIDefinitionMerger()
    merged = merger.merge(parts)
    components_filter = APIComponentsFilter()

    processor = SwaggerProcessor(
        file_loader=FileService(),
        splitter=splitter,
        merger=merger,
        components_filter=components_filter,
        file_service=FileService(),
        config=Config(),
    )
    processor.base_definition = base_yaml

    api_verb = next(p for p in merged if isinstance(p, APIVerb))
    full_yaml = processor.get_api_verb_content(api_verb)
    reconstructed = yaml.safe_load(full_yaml)

    assert "/api/v1/items" not in base_yaml
    assert "/api/v1/items" in reconstructed["paths"]
    assert "get" in reconstructed["paths"]["/api/v1/items"]

    assert "https://api.example.com" not in api_verb.yaml
    assert reconstructed["openapi"] == "3.0.0"
    assert reconstructed["servers"] == [{"url": "https://api.example.com"}]
