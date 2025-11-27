from src.processors.postman.postman_utils import PostmanUtils
from src.processors.postman.models import RequestData


def test_extract_variables_with_valid_data():
    data = {
        "variable": [
            {"key": "baseUrl", "value": "https://api.example.com"},
            {"key": "apiKey", "value": "secret-key"},
        ]
    }

    result = PostmanUtils.extract_variables(data)

    assert len(result) == 2
    assert result[0] == {"key": "baseUrl", "value": "https://api.example.com"}
    assert result[1] == {"key": "apiKey", "value": "secret-key"}


def test_extract_variables_with_no_variables():
    data = {"info": {"name": "Collection"}}

    result = PostmanUtils.extract_variables(data)

    assert result == []


def test_extract_variables_with_empty_variable_array():
    data = {"variable": []}

    result = PostmanUtils.extract_variables(data)

    assert result == []


def test_extract_variables_with_invalid_variable_format():
    data = {
        "variable": [
            {"key": "valid", "value": "value"},
            {"key": "missing_value"},
            {"value": "missing_key"},
            "not_a_dict",
        ]
    }

    result = PostmanUtils.extract_variables(data)

    assert len(result) == 1
    assert result[0] == {"key": "valid", "value": "value"}


def test_extract_requests_with_simple_request():
    data = {"item": [{"name": "Get User", "request": {"method": "GET", "url": "/users/123"}}]}

    result = PostmanUtils.extract_requests(data)

    assert len(result) == 1
    assert result[0].verb == "GET"
    assert result[0].path == "/users/123"
    assert result[0].name == "getUser"


def test_extract_requests_with_nested_folders():
    data = {
        "item": [
            {
                "name": "Users",
                "item": [{"name": "Get User", "request": {"method": "GET", "url": "/users/123"}}],
            }
        ]
    }

    result = PostmanUtils.extract_requests(data)

    assert len(result) == 1
    assert result[0].file_path == "src/tests/users/getUser"


def test_extract_requests_with_deeply_nested_folders():
    data = {
        "item": [
            {
                "name": "API",
                "item": [
                    {
                        "name": "V1",
                        "item": [
                            {"name": "Get Resource", "request": {"method": "GET", "url": "/api/v1/resource"}}
                        ],
                    }
                ],
            }
        ]
    }

    result = PostmanUtils.extract_requests(data)

    assert len(result) == 1
    assert result[0].file_path == "src/tests/api/v1/getResource"
    assert result[0].path == "/v1/resource"  # Path normalized: /api prefix removed


def test_extract_requests_skips_duplicates():
    data = {
        "item": [
            {"name": "Get User", "request": {"method": "GET", "url": "/users/123"}},
            {"name": "Get User", "request": {"method": "GET", "url": "/users/456"}},
        ]
    }

    result = PostmanUtils.extract_requests(data)

    assert len(result) == 1


def test_extract_requests_with_non_standard_dict_structure():
    data = {
        "metadata": {"version": "1.0"},
        "content": [{"name": "Test Request", "request": {"method": "GET", "url": "/test"}}],
    }

    result = PostmanUtils.extract_requests(data)

    assert len(result) == 1
    assert result[0].verb == "GET"
    assert result[0].path == "/test"


def test_extract_request_data_with_dict_url():
    data = {
        "name": "Test Request",
        "request": {"method": "POST", "url": {"raw": "/api/endpoint"}, "body": {"raw": '{"name": "test"}'}},
        "event": [
            {"listen": "prerequest", "script": {"exec": ["console.log('pre')"]}},
            {"listen": "test", "script": {"exec": ["pm.test('ok', () => {})"]}},
        ],
    }

    result = PostmanUtils.extract_request_data(data, "/api")

    assert result.verb == "POST"
    assert result.path == "/endpoint"  # Path normalized: /api prefix removed
    assert result.body == {"name": "test"}
    assert result.prerequest == ["console.log('pre')"]
    assert result.script == ["pm.test('ok', () => {})"]
    assert result.file_path == "src/tests/api/testRequest"


def test_extract_request_data_with_dict_url_path_and_query_arrays():
    """Test that extract_request_data correctly reconstructs path with query params
    from Postman URL dict format."""
    data = {
        "name": "Get Users",
        "request": {
            "method": "GET",
            "url": {
                "raw": "{{BASEURL}}/api/users?page=1&limit=10",
                "host": ["{{BASEURL}}"],
                "path": ["users"],
                "query": [
                    {"key": "page", "value": "1"},
                    {"key": "limit", "value": "10"},
                ],
            },
        },
    }

    result = PostmanUtils.extract_request_data(data, "/api")

    # Path should include query params
    assert result.verb == "GET"
    assert result.path == "/users?page=1&limit=10"  # Query params should be included
    assert "page" in result.path
    assert "limit" in result.path


def test_extract_request_data_with_dict_url_path_array_only():
    """Test that extract_request_data handles URL dict with path array but no query array."""
    data = {
        "name": "Get User",
        "request": {
            "method": "GET",
            "url": {
                "path": ["users", "123"],
            },
        },
    }

    result = PostmanUtils.extract_request_data(data, None)

    assert result.verb == "GET"
    assert result.path == "/users/123"  # No query params, just path


def test_extract_request_data_with_dict_url_prefers_raw_over_path():
    """Test that extract_request_data prefers 'raw' field over path array when both are present."""
    data = {
        "name": "Test Request",
        "request": {
            "method": "GET",
            "url": {
                "raw": "/api/users?page=1&limit=10",
                "path": ["users"],  # Should be ignored when raw is present
                "query": [{"key": "other", "value": "param"}],  # Should be ignored when raw is present
            },
        },
    }

    result = PostmanUtils.extract_request_data(data, "/api")

    assert result.path == "/users?page=1&limit=10"  # Should use raw, not reconstruct from path+query


def test_extract_request_data_with_string_url():
    data = {"name": "Test", "request": {"method": "GET", "url": "/simple/path"}}

    result = PostmanUtils.extract_request_data(data, "")

    assert result.path == "/simple/path"


def test_extract_request_data_with_invalid_json_body():
    data = {"name": "Test", "request": {"method": "POST", "url": "/test", "body": {"raw": "not valid json"}}}

    result = PostmanUtils.extract_request_data(data, "")

    assert result.body == {}


def test_extract_request_data_with_empty_body():
    data = {"name": "Test", "request": {"method": "GET", "url": "/test"}}

    result = PostmanUtils.extract_request_data(data, "")

    assert result.body == {}


def test_extract_request_data_normalizes_api_prefix():
    """Test that /api prefix is removed by default"""
    data = {"name": "Test", "request": {"method": "GET", "url": "/api/users"}}

    result = PostmanUtils.extract_request_data(data, "")

    assert result.path == "/users"


def test_extract_requests_normalizes_paths():
    """Test that extract_requests normalizes paths in all requests"""
    data = {
        "item": [
            {"name": "Get Users", "request": {"method": "GET", "url": "/api/users"}},
            {"name": "Get Orders", "request": {"method": "GET", "url": "/api/v1/orders"}},
            {"name": "Get Products", "request": {"method": "GET", "url": "/products"}},
        ]
    }

    result = PostmanUtils.extract_requests(data)

    assert len(result) == 3
    assert result[0].path == "/users"  # /api/users -> /users
    assert result[1].path == "/v1/orders"  # /api/v1/orders -> /v1/orders
    assert result[2].path == "/products"  # /products unchanged


def test_extract_verb_path_info_groups_by_path_and_verb():
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="",
            path="/users/123",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test1",
        ),
        RequestData(
            service="",
            file_path="test2",
            prefix="",
            path="/users/123",
            verb="POST",
            body={"name": "John"},
            prerequest=[],
            script=[],
            name="test2",
        ),
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 2
    get_verb = next(v for v in result if v.verb == "GET")
    post_verb = next(v for v in result if v.verb == "POST")
    assert get_verb.path == "/users/123"
    assert post_verb.path == "/users/123"
    assert get_verb.root_path == "/users"
    assert post_verb.root_path == "/users"


def test_extract_verb_path_info_removes_query_params():
    requests = [
        RequestData(
            service="",
            file_path="test",
            prefix="",
            path="/users?sort=name&page=1",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test",
        )
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 1
    assert result[0].path == "/users"
    assert "sort" in result[0].query_params
    assert "page" in result[0].query_params


def test_extract_verb_path_info_aggregates_query_params():
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="",
            path="/users?sort=name",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test1",
        ),
        RequestData(
            service="",
            file_path="test2",
            prefix="",
            path="/users?include=profile",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test2",
        ),
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 1
    assert "sort" in result[0].query_params
    assert "include" in result[0].query_params


def test_extract_verb_path_info_aggregates_body_attributes():
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="",
            path="/users",
            verb="POST",
            body={"name": "John"},
            prerequest=[],
            script=[],
            name="test1",
        ),
        RequestData(
            service="",
            file_path="test2",
            prefix="",
            path="/users",
            verb="POST",
            body={"email": "john@example.com"},
            prerequest=[],
            script=[],
            name="test2",
        ),
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 1
    assert "name" in result[0].body_attributes
    assert "email" in result[0].body_attributes


def test_extract_verb_path_info_aggregates_scripts():
    """Test that scripts are aggregated from multiple requests with the same verb and path."""
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="",
            path="/users",
            verb="POST",
            body={},
            prerequest=[],
            script=["pm.test('test1', () => {})", "pm.expect(1).to.equal(1)"],
            name="test1",
        ),
        RequestData(
            service="",
            file_path="test2",
            prefix="",
            path="/users",
            verb="POST",
            body={},
            prerequest=[],
            script=["pm.test('test2', () => {})"],
            name="test2",
        ),
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 1
    assert len(result[0].script) == 3
    assert "pm.test('test1', () => {})" in result[0].script
    assert "pm.expect(1).to.equal(1)" in result[0].script
    assert "pm.test('test2', () => {})" in result[0].script


def test_extract_verb_path_info_scripts_filtered_by_verb():
    """Test that scripts are only collected from requests matching the current verb."""
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="",
            path="/users",
            verb="GET",
            body={},
            prerequest=[],
            script=["pm.test('GET test', () => {})"],
            name="test1",
        ),
        RequestData(
            service="",
            file_path="test2",
            prefix="",
            path="/users",
            verb="POST",
            body={},
            prerequest=[],
            script=["pm.test('POST test', () => {})"],
            name="test2",
        ),
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 2
    get_verb = next(v for v in result if v.verb == "GET")
    post_verb = next(v for v in result if v.verb == "POST")
    assert len(get_verb.script) == 1
    assert "pm.test('GET test', () => {})" in get_verb.script
    assert "pm.test('POST test', () => {})" not in get_verb.script
    assert len(post_verb.script) == 1
    assert "pm.test('POST test', () => {})" in post_verb.script
    assert "pm.test('GET test', () => {})" not in post_verb.script


def test_extract_verb_path_info_handles_empty_scripts():
    """Test that empty scripts are handled correctly."""
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="",
            path="/users",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test1",
        ),
        RequestData(
            service="",
            file_path="test2",
            prefix="",
            path="/users",
            verb="GET",
            body={},
            prerequest=[],
            script=["pm.test('test', () => {})"],
            name="test2",
        ),
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 1
    assert len(result[0].script) == 1
    assert "pm.test('test', () => {})" in result[0].script


def test_extract_verb_path_info_scripts_with_multiple_script_lines():
    """Test that scripts with multiple lines per request are handled correctly."""
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="",
            path="/users",
            verb="POST",
            body={},
            prerequest=[],
            script=[
                "pm.test('Status code is 200', () => {",
                "    pm.response.to.have.status(200);",
                "});",
            ],
            name="test1",
        ),
        RequestData(
            service="",
            file_path="test2",
            prefix="",
            path="/users",
            verb="POST",
            body={},
            prerequest=[],
            script=[
                "pm.test('Response has body', () => {",
                "    pm.expect(pm.response.json()).to.exist;",
                "});",
            ],
            name="test2",
        ),
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 1
    assert len(result[0].script) == 6  # 3 lines from test1 + 3 lines from test2
    assert "pm.test('Status code is 200', () => {" in result[0].script
    assert "    pm.response.to.have.status(200);" in result[0].script
    assert "pm.test('Response has body', () => {" in result[0].script


def test_group_request_data_by_service():
    requests = [
        RequestData(
            service="/users",
            prefix="",
            file_path="test1",
            path="/users/123",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test1",
        ),
        RequestData(
            service="/orders",
            file_path="test2",
            prefix="",
            path="/orders/456",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test2",
        ),
    ]

    result = PostmanUtils.group_request_data_by_service(requests)

    assert "/users" in result
    assert "/orders" in result
    assert len(result["/users"]) == 1
    assert len(result["/orders"]) == 1
    assert result["/users"][0].path == "/users/123"
    assert result["/orders"][0].path == "/orders/456"


def test_accumulate_query_params_with_string_values():
    params = {}

    PostmanUtils.accumulate_query_params(params, "name=john&age=30")

    assert params["name"] == "string"
    assert params["age"] == "number"


def test_accumulate_query_params_with_number_then_string():
    params = {"age": "number"}

    PostmanUtils.accumulate_query_params(params, "age=thirty")

    assert params["age"] == "string"


def test_accumulate_query_params_with_string_then_number():
    params = {"age": "string"}

    PostmanUtils.accumulate_query_params(params, "age=30")

    assert params["age"] == "string"


def test_accumulate_query_params_with_empty_values():
    params = {}

    PostmanUtils.accumulate_query_params(params, "flag=&other=")

    assert "flag" in params
    assert "other" in params


def test_accumulate_query_params_with_blank_names():
    params = {}

    PostmanUtils.accumulate_query_params(params, "=value&name=test")

    assert "" not in params
    assert "name" in params


def test_accumulate_query_params_with_decimal_numbers():
    params = {}

    PostmanUtils.accumulate_query_params(params, "price=19.99&quantity=5")

    assert params["price"] == "string"
    assert params["quantity"] == "number"


def test_accumulate_query_params_with_negative_numbers():
    params = {}

    PostmanUtils.accumulate_query_params(params, "temperature=-5&count=10")

    assert params["temperature"] == "string"
    assert params["count"] == "number"


def test_accumulate_query_params_with_leading_zeros():
    params = {}

    PostmanUtils.accumulate_query_params(params, "code=007&id=123")

    assert params["code"] == "number"
    assert params["id"] == "number"


def test_item_is_a_test_case_with_request():
    item = {"request": {"method": "GET"}}

    result = PostmanUtils.item_is_a_test_case(item)

    assert result is True


def test_item_is_a_test_case_with_event_request():
    item = {"event": [{"listen": "test", "request": {"method": "GET"}}]}

    result = PostmanUtils.item_is_a_test_case(item)

    assert result is True


def test_item_is_a_test_case_with_folder():
    item = {"name": "Folder", "item": []}

    result = PostmanUtils.item_is_a_test_case(item)

    assert result is False


def test_item_is_a_test_case_with_non_dict():
    result = PostmanUtils.item_is_a_test_case("not a dict")

    assert result is False


def test_to_camel_case_basic():
    result = PostmanUtils.to_camel_case("Get User")

    assert result == "getUser"


def test_to_camel_case_with_special_chars():
    result = PostmanUtils.to_camel_case("get-user-by_id")

    assert result == "getUserById"


def test_to_camel_case_with_numbers():
    result = PostmanUtils.to_camel_case("get user 123")

    assert result == "getUser123"


def test_to_camel_case_empty_string():
    result = PostmanUtils.to_camel_case("")

    assert result == ""


def test_to_camel_case_only_special_chars():
    result = PostmanUtils.to_camel_case("---___")

    assert result == ""


def test_accumulate_request_body_attributes_with_strings():
    attrs = {}
    body = {"name": "John", "age": "30", "city": "NYC"}

    PostmanUtils._accumulate_request_body_attributes(attrs, body)

    assert attrs["name"] == "string"
    assert attrs["age"] == "number"
    assert attrs["city"] == "string"


def test_accumulate_request_body_attributes_with_nested_objects():
    attrs = {}
    body = {"user": {"name": "John", "age": "30"}}

    PostmanUtils._accumulate_request_body_attributes(attrs, body)

    assert "userObject" in attrs
    assert isinstance(attrs["userObject"], dict)
    assert attrs["userObject"]["name"] == "string"
    assert attrs["userObject"]["age"] == "number"


def test_accumulate_request_body_attributes_with_arrays():
    attrs = {}
    body = {"items": [1, 2, 3]}

    PostmanUtils._accumulate_request_body_attributes(attrs, body)

    assert attrs["itemsObject"] == "array"


def test_accumulate_request_body_attributes_upgrades_number_to_string():
    attrs = {"age": "number"}
    body = {"age": "thirty"}

    PostmanUtils._accumulate_request_body_attributes(attrs, body)

    assert attrs["age"] == "string"


def test_accumulate_request_body_attributes_keeps_string():
    attrs = {"age": "string"}
    body = {"age": "30"}

    PostmanUtils._accumulate_request_body_attributes(attrs, body)

    assert attrs["age"] == "string"


def test_map_object_attributes_with_primitives():
    obj = {"name": "John", "age": "30", "active": "true"}

    result = PostmanUtils._map_object_attributes(obj)

    assert result["name"] == "string"
    assert result["age"] == "number"
    assert result["active"] == "string"


def test_map_object_attributes_with_nested_objects():
    obj = {"user": {"profile": {"name": "John"}}}

    result = PostmanUtils._map_object_attributes(obj)

    assert "userObject" in result
    assert "profileObject" in result["userObject"]
    assert result["userObject"]["profileObject"]["name"] == "string"


def test_map_object_attributes_with_arrays():
    obj = {"tags": ["tag1", "tag2"]}

    result = PostmanUtils._map_object_attributes(obj)

    assert result["tagsObject"] == "array"


def test_map_object_attributes_empty_object():
    result = PostmanUtils._map_object_attributes({})

    assert result == {}


def test_extract_verb_path_info_includes_prefix_in_root_path():
    """Test that prefix is included in root_path when present."""
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="/api",
            path="/users/123",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test1",
        )
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 1
    assert result[0].root_path == "/api/users"


def test_extract_verb_path_info_with_empty_prefix():
    """Test that root_path works correctly when prefix is empty (backward compatible)."""
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="",
            path="/users/123",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test1",
        )
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 1
    assert result[0].root_path == "/users"


def test_extract_verb_path_info_with_version_prefix():
    """Test that prefix works correctly with versioned paths."""
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="/api",
            path="/v1/pets/123",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test1",
        )
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 1
    assert result[0].root_path == "/api/v1/pets"


def test_extract_verb_path_info_with_multiple_requests_same_prefix():
    """Test that multiple requests with the same prefix all use that prefix in root_path.
    Note: Different base paths create separate groups, but all use the prefix from requests[0]."""
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="/api",
            path="/users/123",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test1",
        ),
        RequestData(
            service="",
            file_path="test2",
            prefix="/api",
            path="/users/456",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test2",
        ),
        RequestData(
            service="",
            file_path="test3",
            prefix="/api",
            path="/users/789",
            verb="POST",
            body={},
            prerequest=[],
            script=[],
            name="test3",
        ),
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 3
    for verb_info in result:
        assert verb_info.root_path == "/api/users"


def test_extract_verb_path_info_with_query_params_and_prefix():
    """Test that prefix is included in root_path even when query params are present."""
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="/api",
            path="/users?sort=name&page=1",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test1",
        )
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 1
    assert result[0].root_path == "/api/users"
    assert result[0].path == "/users"
    assert "sort" in result[0].query_params


def test_extract_verb_path_info_with_custom_prefix():
    """Test that custom prefixes (not /api) work correctly."""
    requests = [
        RequestData(
            service="",
            file_path="test1",
            prefix="/custom",
            path="/orders/123",
            verb="GET",
            body={},
            prerequest=[],
            script=[],
            name="test1",
        )
    ]

    result = PostmanUtils.extract_verb_path_info(requests)

    assert len(result) == 1
    assert result[0].root_path == "/custom/orders"
