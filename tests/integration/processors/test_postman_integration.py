"""
Integration tests for Postman processor end-to-end workflows.
These tests use real Postman collection fixtures and verify the complete processing pipeline.
"""

import json
import pytest

from src.processors.postman_processor import PostmanProcessor
from src.processors.postman.models import RequestData, VerbInfo
from src.services.file_service import FileService
from src.configuration.config import Config
from src.models import APIDefinition


@pytest.fixture
def temp_destination(tmp_path):
    """Create a temporary destination folder"""
    dest = tmp_path / "output"
    dest.mkdir()
    return dest


@pytest.fixture
def file_service():
    """Create a real FileService instance"""
    return FileService()


@pytest.fixture
def config(temp_destination):
    """Create a Config instance with temporary destination"""
    config = Config()
    config.destination_folder = str(temp_destination)
    return config


@pytest.fixture
def postman_processor(file_service, config):
    """Create a PostmanProcessor instance with real dependencies"""
    return PostmanProcessor(file_service=file_service, config=config)


@pytest.fixture
def simple_collection_path():
    """Path to the simple Postman collection fixture"""
    return "tests/fixtures/postman/simple_collection.json"


@pytest.fixture
def complex_collection_path():
    """Path to the complex Postman collection fixture"""
    return "tests/fixtures/postman/complex_collection.json"


class TestSimpleCollectionProcessing:
    """Integration tests using the simple Postman collection"""

    def test_process_simple_collection_end_to_end(self, postman_processor, simple_collection_path):
        """Test processing a simple collection from start to finish"""
        api_definition = postman_processor.process_api_definition(simple_collection_path)

        assert isinstance(api_definition, APIDefinition)
        assert len(api_definition.definitions) > 0
        assert len(api_definition.variables) == 2

        variable_keys = {var["key"] for var in api_definition.variables}
        assert "BASEURL" in variable_keys
        assert "API_KEY" in variable_keys

        assert all(isinstance(req, RequestData) for req in api_definition.definitions)

        first_request = api_definition.definitions[0]
        assert first_request.name != ""
        assert first_request.verb in ["GET", "POST", "PUT", "DELETE", "PATCH"]
        assert first_request.full_path != ""

    def test_generate_env_file_from_simple_collection(
        self, postman_processor, simple_collection_path, temp_destination
    ):
        """Test .env file generation from simple collection"""
        api_definition = postman_processor.process_api_definition(simple_collection_path)

        postman_processor.create_dot_env(api_definition)

        env_file_path = temp_destination / ".env"
        assert env_file_path.exists()

        env_content = env_file_path.read_text()
        assert "BASEURL=https://api.example.com" in env_content
        assert "API_KEY=test-api-key-123" in env_content

    def test_group_paths_by_service_simple_collection(self, postman_processor, simple_collection_path):
        """Test path grouping and service mapping for simple collection"""
        api_definition = postman_processor.process_api_definition(simple_collection_path)

        api_paths = postman_processor.get_api_paths(api_definition)

        assert len(api_paths) > 0
        service_verbs = api_paths[0]

        assert isinstance(service_verbs, list)
        assert len(service_verbs) > 0
        assert all(isinstance(v, VerbInfo) for v in service_verbs)

    def test_get_api_verbs_with_service_tags(self, postman_processor, simple_collection_path):
        """Test that API verbs get properly tagged with services"""
        api_definition = postman_processor.process_api_definition(simple_collection_path)

        postman_processor.get_api_paths(api_definition)

        api_verbs = postman_processor.get_api_verbs(api_definition)

        assert len(api_verbs) > 0
        assert all(verb.service != "" for verb in api_verbs)

    def test_get_api_paths_and_verbs_path_matching(self, postman_processor, simple_collection_path):
        """Test that get_api_paths and get_api_verbs correctly match paths with and without query params"""
        api_definition = postman_processor.process_api_definition(simple_collection_path)

        # Get API paths
        api_paths = postman_processor.get_api_paths(api_definition)

        # Verify api_paths structure
        assert len(api_paths) > 0
        assert all(isinstance(path_group, list) for path_group in api_paths)
        assert all(isinstance(verb_info, VerbInfo) for path_group in api_paths for verb_info in path_group)

        api_verbs = postman_processor.get_api_verbs(api_definition)

        # Verify all verbs have services assigned
        assert len(api_verbs) > 0
        assert all(verb.service != "" for verb in api_verbs), "All verbs should have a service assigned"

        # Build service_dict from api_paths for verification
        service_dict_paths = {}
        for path_group in api_paths:
            service_name = postman_processor.get_api_path_name(path_group)
            if service_name:
                root_path = f"/{service_name}"
                service_dict_paths[root_path] = {verb.path for verb in path_group}

        # Verify each verb's path matches a path in its assigned service
        for verb in api_verbs:
            verb_path_no_query = verb.path.split("?")[0]
            assert verb.service in service_dict_paths, f"Service '{verb.service}' not found in service_dict"
            assert verb_path_no_query in service_dict_paths[verb.service], (
                f"Path '{verb_path_no_query}' not found in service '{verb.service}'. "
                f"Available paths: {service_dict_paths[verb.service]}"
            )


class TestComplexCollectionProcessing:
    """Integration tests using the complex Postman collection"""

    def test_process_complex_collection_with_nested_folders(self, postman_processor, complex_collection_path):
        """Test processing a complex collection with nested folder structure"""
        api_definition = postman_processor.process_api_definition(complex_collection_path)

        assert len(api_definition.definitions) >= 8

        assert len(api_definition.variables) == 3
        variable_keys = {var["key"] for var in api_definition.variables}
        assert "BASEURL" in variable_keys
        assert "AUTH_TOKEN" in variable_keys
        assert "API_VERSION" in variable_keys

        file_paths = [req.file_path for req in api_definition.definitions]
        assert any("userService" in path for path in file_paths)
        assert any("productService" in path for path in file_paths)

    def test_multiple_services_identified_in_complex_collection(
        self, postman_processor, complex_collection_path
    ):
        """Test that multiple services are correctly identified and grouped"""
        api_definition = postman_processor.process_api_definition(complex_collection_path)
        api_paths = postman_processor.get_api_paths(api_definition)

        assert len(api_paths) >= 3

        services = {postman_processor.get_api_path_name(path) for path in api_paths}
        assert "users" in services
        assert "products" in services
        assert "orders" in services or "categories" in services

    def test_get_api_verbs_matches_paths_with_query_params_complex_collection(
        self, postman_processor, complex_collection_path
    ):
        """Test that get_api_verbs correctly matches paths with query parameters in complex collection"""
        api_definition = postman_processor.process_api_definition(complex_collection_path)

        # Get API paths
        api_paths = postman_processor.get_api_paths(api_definition)

        api_verbs = postman_processor.get_api_verbs(api_definition)

        # Verify all verbs have services assigned
        assert len(api_verbs) > 0
        verbs_without_service = [v for v in api_verbs if v.service == ""]
        assert len(verbs_without_service) == 0, (
            f"Found {len(verbs_without_service)} verbs without service assignment: "
            f"{[(v.path, v.verb) for v in verbs_without_service]}"
        )

        # Build service_dict from api_paths for verification
        service_dict_paths = {}
        service_prefixes = {}  # Track prefix for each service
        for path_group in api_paths:
            service_name = postman_processor.get_api_path_name(path_group)
            if service_name:
                root_path = f"/{service_name}"
                service_dict_paths[root_path] = {verb.path for verb in path_group}
                # Extract prefix from root_path: if root_path is "/api/users" and service is "/users",
                # prefix is "/api" (everything before "/users")
                if path_group and path_group[0].root_path:
                    root_path_str = path_group[0].root_path
                    service_with_slash = root_path
                    # Remove service from end of root_path to get prefix
                    if root_path_str.endswith(service_with_slash):
                        prefix = root_path_str[: -len(service_with_slash)]
                        service_prefixes[root_path] = prefix
                    else:
                        service_prefixes[root_path] = ""
                else:
                    service_prefixes[root_path] = ""

        # Verify that each verb's path (without query params) matches a path in its assigned service
        for verb in api_verbs:
            verb_path_no_query = verb.path.split("?")[0]
            service = verb.service

            # Find the service in service_dict
            assert (
                service in service_dict_paths
            ), f"Service '{service}' not found in service_dict for verb {verb.verb} {verb.path}"

            # Get all paths for this service
            service_paths = service_dict_paths[service]

            # Get the prefix for this service (from VerbInfo paths)
            service_prefix = service_prefixes.get(service, verb.prefix or "")

            verb_path_with_prefix = (
                service_prefix + verb_path_no_query if service_prefix else verb_path_no_query
            )

            assert verb_path_with_prefix in service_paths, (
                f"Path '{verb_path_with_prefix}' (from verb {verb.verb} {verb.path} "
                f"with service prefix {service_prefix}) not found in service '{service}'. "
                f"Available paths in service: {service_paths}. "
                f"Service dict keys: {list(service_dict_paths.keys())}"
            )

    def test_query_params_extracted_from_complex_collection(self, postman_processor, complex_collection_path):
        """Test query parameter extraction and type inference"""
        api_definition = postman_processor.process_api_definition(complex_collection_path)
        api_paths = postman_processor.get_api_paths(api_definition)

        all_verbs = [verb for service_verbs in api_paths for verb in service_verbs]
        verbs_with_query_params = [v for v in all_verbs if v.query_params]

        assert len(verbs_with_query_params) > 0

        for verb in verbs_with_query_params:
            for param, param_type in verb.query_params.items():
                assert param_type in ["string", "number"]

    def test_body_attributes_extracted_with_nested_objects(self, postman_processor, complex_collection_path):
        """Test body attribute extraction including nested objects"""
        api_definition = postman_processor.process_api_definition(complex_collection_path)
        api_paths = postman_processor.get_api_paths(api_definition)

        all_verbs = [verb for service_verbs in api_paths for verb in service_verbs]
        verbs_with_body = [v for v in all_verbs if v.body_attributes and v.verb in ["POST", "PUT"]]

        assert len(verbs_with_body) > 0

        for verb in verbs_with_body:
            has_nested = any("Object" in key for key in verb.body_attributes.keys())
            if has_nested:
                for key, value in verb.body_attributes.items():
                    if "Object" in key:
                        assert isinstance(value, dict) or value == "array"
                break

    def test_scripts_preserved_in_complex_collection(self, postman_processor, complex_collection_path):
        """Test that prerequest and test scripts are preserved"""
        api_definition = postman_processor.process_api_definition(complex_collection_path)

        requests_with_prerequest = [req for req in api_definition.definitions if req.prerequest]
        requests_with_test_script = [req for req in api_definition.definitions if req.script]

        assert len(requests_with_prerequest) > 0
        assert len(requests_with_test_script) > 0

        for req in requests_with_prerequest:
            assert isinstance(req.prerequest, list)
            assert all(isinstance(line, str) for line in req.prerequest)

        for req in requests_with_test_script:
            assert isinstance(req.script, list)
            assert all(isinstance(line, str) for line in req.script)


class TestFrameworkGeneration:
    """Integration tests for framework file generation"""

    def test_create_run_order_file_from_collection(
        self, postman_processor, simple_collection_path, temp_destination
    ):
        """Test runTestsInOrder.js file generation"""
        api_definition = postman_processor.process_api_definition(simple_collection_path)

        postman_processor._create_run_order_file(str(temp_destination), api_definition)

        run_order_file = temp_destination / "runTestsInOrder.js"
        assert run_order_file.exists()

        content = run_order_file.read_text()
        assert "// This file runs the tests in order" in content

        for req in api_definition.definitions:
            expected_import = f'import "./{req.file_path}.spec.ts";'
            assert expected_import in content

    def test_update_package_json_from_collection(
        self, postman_processor, simple_collection_path, temp_destination
    ):
        """Test package.json update with test script"""
        package_json_path = temp_destination / "package.json"
        initial_package = {
            "name": "test-framework",
            "version": "1.0.0",
            "dependencies": {},
        }
        package_json_path.write_text(json.dumps(initial_package, indent=2))

        postman_processor._update_package_dot_json(str(temp_destination))

        updated_package = json.loads(package_json_path.read_text())
        assert "scripts" in updated_package
        assert "test" in updated_package["scripts"]
        assert "mocha runTestsInOrder.js --timeout 10000" in updated_package["scripts"]["test"]

    def test_full_framework_update_workflow(
        self, postman_processor, complex_collection_path, temp_destination
    ):
        """Test complete framework update workflow"""
        api_definition = postman_processor.process_api_definition(complex_collection_path)

        package_json_path = temp_destination / "package.json"
        package_json_path.write_text(json.dumps({"name": "test"}, indent=2))

        postman_processor.update_framework_for_postman(str(temp_destination), api_definition)

        package_data = json.loads(package_json_path.read_text())
        assert "scripts" in package_data
        assert "test" in package_data["scripts"]

        run_order_file = temp_destination / "runTestsInOrder.js"
        assert run_order_file.exists()


class TestEdgeCases:
    """Integration tests for edge cases and error handling"""

    def test_collection_with_no_variables(self, postman_processor, temp_destination):
        """Test processing collection without variables"""
        collection_path = temp_destination / "no_vars.json"
        collection_data = {"item": [{"name": "Test", "request": {"method": "GET", "url": "/test"}}]}
        collection_path.write_text(json.dumps(collection_data))

        api_definition = postman_processor.process_api_definition(str(collection_path))

        assert len(api_definition.variables) == 0

        postman_processor.create_dot_env(api_definition)
        env_file = temp_destination / ".env"
        assert env_file.exists()
        assert "BASEURL=" in env_file.read_text()

    def test_collection_with_duplicate_request_names(self, postman_processor, temp_destination):
        """Test handling of duplicate request names"""
        collection_path = temp_destination / "duplicates.json"
        collection_data = {
            "item": [
                {"name": "Get User", "request": {"method": "GET", "url": "/users/1"}},
                {"name": "Get User", "request": {"method": "GET", "url": "/users/2"}},
            ]
        }
        collection_path.write_text(json.dumps(collection_data))

        api_definition = postman_processor.process_api_definition(str(collection_path))

        # Should only keep one (first occurrence based on implementation)
        assert len(api_definition.definitions) == 1

    def test_collection_with_malformed_json_body(self, postman_processor, temp_destination):
        """Test handling of malformed JSON in request body"""
        collection_path = temp_destination / "malformed.json"
        collection_data = {
            "item": [
                {
                    "name": "Create",
                    "request": {
                        "method": "POST",
                        "url": "/test",
                        "body": {"raw": "invalid json {"},
                    },
                }
            ]
        }
        collection_path.write_text(json.dumps(collection_data))

        api_definition = postman_processor.process_api_definition(str(collection_path))

        assert len(api_definition.definitions) == 1
        assert api_definition.definitions[0].body == {}

    def test_collection_with_various_url_formats(self, postman_processor, temp_destination):
        """Test handling of different URL formats"""
        collection_path = temp_destination / "url_formats.json"
        collection_data = {
            "item": [
                # String URL
                {"name": "Test1", "request": {"method": "GET", "url": "/test1"}},
                # Dict URL with raw
                {
                    "name": "Test2",
                    "request": {"method": "GET", "url": {"raw": "/test2"}},
                },
                # Missing URL
                {"name": "Test3", "request": {"method": "GET"}},
            ]
        }
        collection_path.write_text(json.dumps(collection_data))

        api_definition = postman_processor.process_api_definition(str(collection_path))

        assert len(api_definition.definitions) == 3
        assert api_definition.definitions[0].path == "/test1"
        assert api_definition.definitions[1].path == "/test2"
        assert api_definition.definitions[2].path == ""


class TestCamelCaseConversion:
    """Integration tests for name conversion in real collections"""

    def test_folder_names_converted_to_camel_case(self, postman_processor, complex_collection_path):
        """Test that folder names are properly converted to camelCase in file paths"""
        api_definition = postman_processor.process_api_definition(complex_collection_path)

        file_paths = [req.file_path for req in api_definition.definitions]

        assert any("userService" in path for path in file_paths)
        assert any("productService" in path for path in file_paths)

        request_names = [req.name for req in api_definition.definitions]
        assert all(name[0].islower() for name in request_names if name)

    def test_request_names_with_special_characters(self, postman_processor, temp_destination):
        """Test conversion of request names with special characters"""
        collection_path = temp_destination / "special_names.json"
        collection_data = {
            "item": [
                {"name": "Get-User-Data", "request": {"method": "GET", "url": "/test1"}},
                {"name": "Create New User!", "request": {"method": "POST", "url": "/test2"}},
                {"name": "Update_User_Status", "request": {"method": "PUT", "url": "/test3"}},
            ]
        }
        collection_path.write_text(json.dumps(collection_data))

        api_definition = postman_processor.process_api_definition(str(collection_path))

        names = [req.name for req in api_definition.definitions]
        assert "getUserData" in names
        assert "createNewUser" in names
        assert "updateUserStatus" in names
