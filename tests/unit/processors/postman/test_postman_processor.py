import json
import pytest

from src.processors.postman_processor import PostmanProcessor
from src.processors.postman.models import RequestData, VerbInfo
from src.configuration.config import Config
from src.services.file_service import FileService
from src.models import APIDefinition, ModelInfo, GeneratedModel, APIModel, APIPath


@pytest.fixture
def temp_config(tmp_path):
    return Config(destination_folder=str(tmp_path))


@pytest.fixture
def file_service():
    return FileService()


@pytest.fixture
def postman_processor(file_service, temp_config):
    return PostmanProcessor(file_service, temp_config)


@pytest.fixture
def sample_postman_collection():
    return {
        "info": {"_postman_id": "test-123", "name": "Test Collection"},
        "variable": [
            {"key": "baseUrl", "value": "https://api.example.com"},
            {"key": "apiKey", "value": "test-key"},
        ],
        "item": [
            {
                "name": "Users",
                "item": [
                    {
                        "name": "Get User",
                        "request": {
                            "method": "GET",
                            "url": {"raw": "/users/123?include=profile"},
                        },
                        "event": [
                            {"listen": "prerequest", "script": {"exec": ["console.log('pre')"]}},
                            {"listen": "test", "script": {"exec": ["pm.test('ok', function() {})"]}},
                        ],
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_request_data():
    return RequestData(
        root_path="users",
        file_path="src/tests/users/getUser",
        prefix="",
        full_path="/users/123",
        verb="GET",
        body={},
        prerequest=["console.log('pre')"],
        script=["pm.test('ok', function() {})"],
        name="getUser",
    )


def test_process_api_definition_returns_api_definition(
    postman_processor, tmp_path, sample_postman_collection
):
    postman_file = tmp_path / "collection.json"
    postman_file.write_text(json.dumps(sample_postman_collection))

    result = postman_processor.process_api_definition(str(postman_file))

    assert isinstance(result, APIDefinition)
    assert len(result.definitions) > 0
    assert len(result.variables) == 2


def test_process_api_definition_extracts_variables(postman_processor, tmp_path, sample_postman_collection):
    postman_file = tmp_path / "collection.json"
    postman_file.write_text(json.dumps(sample_postman_collection))

    result = postman_processor.process_api_definition(str(postman_file))

    assert result.variables[0]["key"] == "baseUrl"
    assert result.variables[0]["value"] == "https://api.example.com"
    assert result.variables[1]["key"] == "apiKey"
    assert result.variables[1]["value"] == "test-key"


def test_process_api_definition_extracts_requests(postman_processor, tmp_path, sample_postman_collection):
    postman_file = tmp_path / "collection.json"
    postman_file.write_text(json.dumps(sample_postman_collection))

    result = postman_processor.process_api_definition(str(postman_file))

    assert len(result.definitions) == 1
    assert isinstance(result.definitions[0], RequestData)


def test_process_api_definition_with_empty_collection(postman_processor, tmp_path):
    empty_data = {"info": {"name": "Empty"}, "item": []}
    postman_file = tmp_path / "empty.json"
    postman_file.write_text(json.dumps(empty_data))

    result = postman_processor.process_api_definition(str(postman_file))

    assert isinstance(result, APIDefinition)
    assert len(result.definitions) == 0


def test_create_dot_env_creates_file(postman_processor, tmp_path):
    postman_processor.config.destination_folder = str(tmp_path)
    api_definition = APIDefinition(
        definitions=[],
        variables=[
            {"key": "baseUrl", "value": "https://api.example.com"},
            {"key": "apiKey", "value": "secret-key"},
        ],
    )

    postman_processor.create_dot_env(api_definition)

    env_file = tmp_path / ".env"
    assert env_file.exists()


def test_create_dot_env_formats_variables_correctly(postman_processor, tmp_path):
    postman_processor.config.destination_folder = str(tmp_path)
    api_definition = APIDefinition(
        definitions=[],
        variables=[
            {"key": "baseUrl", "value": "https://api.example.com"},
            {"key": "apiKey", "value": "secret-key"},
        ],
    )

    postman_processor.create_dot_env(api_definition)

    env_file = tmp_path / ".env"
    content = env_file.read_text()
    assert "BASEURL=https://api.example.com" in content
    assert "APIKEY=secret-key" in content


def test_create_dot_env_with_no_variables_creates_baseurl(postman_processor, tmp_path):
    postman_processor.config.destination_folder = str(tmp_path)
    api_definition = APIDefinition(definitions=[], variables=[])

    postman_processor.create_dot_env(api_definition)

    env_file = tmp_path / ".env"
    content = env_file.read_text()
    assert "BASEURL=" in content


def test_create_dot_env_uppercases_keys(postman_processor, tmp_path):
    postman_processor.config.destination_folder = str(tmp_path)
    api_definition = APIDefinition(
        definitions=[],
        variables=[
            {"key": "baseUrl", "value": "https://api.example.com"},
            {"key": "mixedCaseKey", "value": "testValue"},
        ],
    )

    postman_processor.create_dot_env(api_definition)

    env_file = tmp_path / ".env"
    content = env_file.read_text()
    assert "BASEURL=https://api.example.com" in content
    assert "MIXEDCASEKEY=testValue" in content
    assert "baseUrl" not in content
    assert "mixedCaseKey" not in content


def test_get_api_paths_returns_list(postman_processor):
    request = RequestData(
        root_path="/users",
        prefix="",
        file_path="test",
        full_path="/users/123",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="test",
    )
    api_definition = APIDefinition(definitions=[request])

    result = postman_processor.get_api_paths(api_definition)

    assert isinstance(result, list)
    assert len(result) == 1


def test_get_api_paths_groups_by_service(postman_processor):
    request1 = RequestData(
        root_path="/users",  # Service is set to root path
        prefix="",
        file_path="test1",
        full_path="/users/123",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="test1",
    )
    request2 = RequestData(
        root_path="/orders",  # Service is set to root path
        prefix="",
        file_path="test2",
        full_path="/orders/456",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="test2",
    )
    api_definition = APIDefinition(definitions=[request1, request2])

    result = postman_processor.get_api_paths(api_definition)

    assert all(isinstance(group, list) for group in result)
    services = {postman_processor.get_api_path_name(group) for group in result}
    assert services == {"users", "orders"}
    for group in result:
        assert len(group) >= 1


def test_get_api_paths_returns_grouped_verb_infos(postman_processor):
    request = RequestData(
        root_path="/users",  # Service is set to root path
        prefix="",
        file_path="test",
        full_path="/users/123",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="test",
    )
    api_definition = APIDefinition(definitions=[request])

    result = postman_processor.get_api_paths(api_definition)

    assert len(result) > 0
    assert all(isinstance(group, list) for group in result)
    assert all(isinstance(verb_info, VerbInfo) for group in result for verb_info in group)


def test_get_api_path_name_returns_service_name(postman_processor):
    api_path = [
        VerbInfo(
            verb="GET", root_path="/users", full_path="/users", query_params={}, body_attributes={}, script=[]
        )
    ]

    result = postman_processor.get_api_path_name(api_path)

    assert result == "users"


def test_get_api_path_name_with_empty_dict(postman_processor):
    result = postman_processor.get_api_path_name([])

    assert result == ""


def test_get_relevant_models_returns_matching_models(postman_processor):
    model_files = [GeneratedModel(path="User.ts", fileContent="interface User {}", summary="User model")]
    all_models = [
        ModelInfo(path="users", files=["User.ts"], models=model_files),
        ModelInfo(path="orders", files=["Order.ts"], models=[]),
    ]
    api_verb = RequestData(
        root_path="users",
        file_path="test",
        prefix="",
        full_path="/users",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="test",
    )

    result = postman_processor.get_relevant_models(all_models, api_verb)

    assert len(result) == 1
    assert isinstance(result[0], GeneratedModel)
    assert result[0].path == "User.ts"
    assert result[0].fileContent == "interface User {}"
    assert result[0].summary == "User model"


def test_get_relevant_models_returns_empty_when_no_match(postman_processor):
    all_models = [ModelInfo(path="users", files=["User.ts"], models=[])]
    api_verb = RequestData(
        root_path="orders",
        file_path="test",
        prefix="",
        full_path="/orders",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="test",
    )

    result = postman_processor.get_relevant_models(all_models, api_verb)

    assert len(result) == 0


def test_get_other_models_excludes_current_service(postman_processor):
    all_models = [
        ModelInfo(path="users", files=["User.ts"], models=[]),
        ModelInfo(path="orders", files=["Order.ts"], models=[]),
        ModelInfo(path="products", files=["Product.ts"], models=[]),
    ]
    api_verb = RequestData(
        root_path="users",
        file_path="test",
        prefix="",
        full_path="/users",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="test",
    )

    result = postman_processor.get_other_models(all_models, api_verb)

    assert len(result) == 2
    assert all(isinstance(m, APIModel) for m in result)
    assert all(m.path != "users" for m in result)


def test_get_other_models_returns_api_model_instances(postman_processor):
    all_models = [
        ModelInfo(path="users", files=["User.ts"], models=[]),
        ModelInfo(path="orders", files=["Order.ts"], models=[]),
    ]
    api_verb = RequestData(
        root_path="users",
        file_path="test",
        prefix="",
        full_path="/users",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="test",
    )

    result = postman_processor.get_other_models(all_models, api_verb)

    assert len(result) == 1
    assert result[0].path == "orders"
    assert result[0].files == ["Order.ts"]


def test_get_api_verb_path(postman_processor, sample_request_data):
    result = postman_processor.get_api_verb_path(sample_request_data)

    assert result == "/users/123"


def test_get_api_verb_rootpath(postman_processor, sample_request_data):
    result = postman_processor.get_api_verb_rootpath(sample_request_data)

    assert result == "users"


def test_get_api_verb_name(postman_processor, sample_request_data):
    result = postman_processor.get_api_verb_name(sample_request_data)

    assert result == "GET"


def test_get_api_verbs_returns_request_data_list(postman_processor):
    request = RequestData(
        root_path="",
        file_path="test",
        prefix="",
        full_path="/users/123",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="test",
    )
    api_definition = APIDefinition(definitions=[request])
    postman_processor.get_api_paths(api_definition)

    result = postman_processor.get_api_verbs(api_definition)

    assert isinstance(result, list)
    assert all(isinstance(r, RequestData) for r in result)


def test_get_api_verbs_tags_with_service(postman_processor):
    # Service is already set when RequestData is created via extract_request_data
    # In this test, we set it manually to match real usage
    request = RequestData(
        root_path="/users",  # Service is set to root path in extract_request_data
        file_path="test",
        prefix="",
        full_path="/users/123",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="test",
    )
    api_definition = APIDefinition(definitions=[request])
    postman_processor.get_api_paths(api_definition)

    result = postman_processor.get_api_verbs(api_definition)

    assert len(result) == 1
    assert result[0].service != ""
    assert result[0].service == "/users"


def test_get_api_verbs_tags_multiple_services_correctly(postman_processor):
    request1 = RequestData(
        root_path="/users",  # Service is set to root path
        file_path="test1",
        prefix="",
        full_path="/users/123",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="test1",
    )
    request2 = RequestData(
        root_path="/orders",  # Service is set to root path
        file_path="test2",
        prefix="",
        full_path="/orders/456",
        verb="POST",
        body={},
        prerequest=[],
        script=[],
        name="test2",
    )
    api_definition = APIDefinition(definitions=[request1, request2])
    postman_processor.get_api_paths(api_definition)

    result = postman_processor.get_api_verbs(api_definition)

    assert len(result) == 2
    users_verb = next((r for r in result if r.path == "/users/123"), None)
    orders_verb = next((r for r in result if r.path == "/orders/456"), None)
    assert users_verb is not None
    assert orders_verb is not None
    assert users_verb.service == "/users"  # Service is root path
    assert orders_verb.service == "/orders"  # Service is root path


def test_get_api_verb_content_returns_json_string(postman_processor, sample_request_data):
    result = postman_processor.get_api_verb_content(sample_request_data)

    assert isinstance(result, str)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_get_api_verb_content_includes_all_fields(postman_processor, sample_request_data):
    result = postman_processor.get_api_verb_content(sample_request_data)

    parsed = json.loads(result)
    assert parsed["service"] == "users"
    assert parsed["file_path"] == "src/tests/users/getUser"
    assert parsed["path"] == "/users/123"
    assert parsed["verb"] == "GET"
    assert parsed["name"] == "getUser"
    assert "body" in parsed
    assert "prerequest" in parsed
    assert "script" in parsed


def test_get_api_path_content_returns_json_string(postman_processor):
    api_path = [
        VerbInfo(
            verb="GET",
            full_path="/users/123",
            query_params={"include": "string"},
            body_attributes={},
            root_path="/users",
            script=[],
        )
    ]

    result = postman_processor.get_api_path_content(api_path)

    assert isinstance(result, str)
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_get_api_path_content_includes_verb_details(postman_processor):
    api_path = [
        VerbInfo(
            verb="GET",
            full_path="/users/123",
            query_params={"include": "string"},
            body_attributes={"name": "string"},
            root_path="/users",
            script=[],
        )
    ]

    result = postman_processor.get_api_path_content(api_path)

    parsed = json.loads(result)
    assert "users" in parsed
    assert len(parsed["users"]) == 1
    assert parsed["users"][0]["verb"] == "GET"
    assert parsed["users"][0]["path"] == "/users/123"
    assert parsed["users"][0]["query_params"] == {"include": "string"}
    assert parsed["users"][0]["body_attributes"] == {"name": "string"}
    assert parsed["users"][0]["root_path"] == "/users"


def test_update_framework_for_postman_creates_run_order_file(postman_processor, tmp_path):
    package_json = tmp_path / "package.json"
    package_json.write_text(json.dumps({"name": "test"}))

    request = RequestData(
        root_path="users",
        file_path="src/tests/users/getUser",
        prefix="",
        full_path="/users",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="getUser",
    )
    api_definition = APIDefinition(definitions=[request])

    postman_processor.update_framework_for_postman(str(tmp_path), api_definition)

    run_order_file = tmp_path / "runTestsInOrder.js"
    assert run_order_file.exists()


def test_update_framework_for_postman_updates_package_json(postman_processor, tmp_path):
    package_data = {"name": "test", "version": "1.0.0"}
    package_json = tmp_path / "package.json"
    package_json.write_text(json.dumps(package_data))

    api_definition = APIDefinition(definitions=[])

    postman_processor.update_framework_for_postman(str(tmp_path), api_definition)

    updated_data = json.loads(package_json.read_text())
    assert "scripts" in updated_data
    assert updated_data["scripts"]["test"] == "mocha runTestsInOrder.js --timeout 10000"


def test_update_package_json_adds_test_script(postman_processor, tmp_path):
    package_data = {"name": "test"}
    package_json = tmp_path / "package.json"
    package_json.write_text(json.dumps(package_data))

    postman_processor._update_package_dot_json(str(tmp_path))

    updated_data = json.loads(package_json.read_text())
    assert updated_data["scripts"]["test"] == "mocha runTestsInOrder.js --timeout 10000"


def test_update_package_json_preserves_existing_scripts(postman_processor, tmp_path):
    package_data = {"name": "test", "scripts": {"build": "tsc", "lint": "eslint ."}}
    package_json = tmp_path / "package.json"
    package_json.write_text(json.dumps(package_data))

    postman_processor._update_package_dot_json(str(tmp_path))

    updated_data = json.loads(package_json.read_text())
    assert updated_data["scripts"]["build"] == "tsc"
    assert updated_data["scripts"]["lint"] == "eslint ."
    assert updated_data["scripts"]["test"] == "mocha runTestsInOrder.js --timeout 10000"


def test_update_package_json_handles_missing_file(postman_processor, tmp_path, caplog):
    postman_processor._update_package_dot_json(str(tmp_path / "nonexistent"))

    assert any("Failed to update package.json" in record.message for record in caplog.records)


def test_create_run_order_file_includes_all_requests(postman_processor, tmp_path):
    request1 = RequestData(
        root_path="users",
        file_path="src/tests/users/getUser",
        prefix="",
        full_path="/users",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="getUser",
    )
    request2 = RequestData(
        root_path="users",
        file_path="src/tests/users/createUser",
        prefix="",
        full_path="/users",
        verb="POST",
        body={},
        prerequest=[],
        script=[],
        name="createUser",
    )
    api_definition = APIDefinition(definitions=[request1, request2])

    postman_processor._create_run_order_file(str(tmp_path), api_definition)

    run_order_file = tmp_path / "runTestsInOrder.js"
    content = run_order_file.read_text()
    assert 'import "./src/tests/users/getUser.spec.ts";' in content
    assert 'import "./src/tests/users/createUser.spec.ts";' in content


def test_create_run_order_file_includes_header_comment(postman_processor, tmp_path):
    api_definition = APIDefinition(definitions=[])

    postman_processor._create_run_order_file(str(tmp_path), api_definition)

    run_order_file = tmp_path / "runTestsInOrder.js"
    content = run_order_file.read_text()
    assert "// This file runs the tests in order" in content


def test_create_run_order_file_skips_non_request_data(postman_processor, tmp_path):
    request = RequestData(
        root_path="users",
        file_path="src/tests/users/getUser",
        prefix="",
        full_path="/users",
        verb="GET",
        body={},
        prerequest=[],
        script=[],
        name="getUser",
    )
    api_path = APIPath(path="/users", yaml="test")
    api_definition = APIDefinition(definitions=[request, api_path])

    postman_processor._create_run_order_file(str(tmp_path), api_definition)

    run_order_file = tmp_path / "runTestsInOrder.js"
    content = run_order_file.read_text()
    lines = content.split("\n")
    import_lines = [line for line in lines if line.startswith("import")]
    assert len(import_lines) == 1
