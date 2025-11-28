from src.processors.swagger import APIDefinitionMerger
from src.models import APIPath, APIVerb
import yaml


def test_merger_merge_two_differente_paths():
    merger = APIDefinitionMerger()

    sample_yaml_str = yaml.dump({"/api/v1/path": {"get": {"description": "path details"}}}, sort_keys=False)

    parts_to_merge = [
        APIPath(full_path="/users/{id}", content=sample_yaml_str),
        APIPath(full_path="/users", content=sample_yaml_str),
        APIVerb(verb="GET", full_path="/users/{id}", root_path="/users", content=sample_yaml_str),
        APIVerb(verb="POST", full_path="/users", root_path="/users", content=sample_yaml_str),
    ]

    merged = merger.merge(parts_to_merge)

    assert len(merged) == 3

    merged_api_paths = [p for p in merged if isinstance(p, APIPath)]
    merged_api_verbs = [p for p in merged if isinstance(p, APIVerb)]

    assert len(merged_api_paths) == 1
    assert len(merged_api_verbs) == 2

    assert merged_api_paths[0].full_path == "/users"
    assert yaml.safe_load(merged_api_paths[0].content) == yaml.safe_load(sample_yaml_str)
    assert merged_api_paths[0].type == "path"

    assert merged_api_verbs[0].full_path == "/users/{id}"
    assert merged_api_verbs[0].verb == "GET"
    assert merged_api_verbs[0].root_path == "/users"
    assert yaml.safe_load(merged_api_verbs[0].content) == yaml.safe_load(sample_yaml_str)
    assert merged_api_verbs[0].type == "verb"

    assert merged_api_verbs[1].full_path == "/users"
    assert merged_api_verbs[1].verb == "POST"
    assert merged_api_verbs[1].root_path == "/users"
    assert yaml.safe_load(merged_api_verbs[1].content) == yaml.safe_load(sample_yaml_str)
    assert merged_api_verbs[1].type == "verb"


def test_merger_merge_two_equal_paths():
    merger = APIDefinitionMerger()

    sample_yaml_str = yaml.dump({"/api/v1/users": {"get": {"description": "user details"}}}, sort_keys=False)

    parts_to_merge = [
        APIPath(full_path="/users", content=sample_yaml_str),
        APIPath(full_path="/users", content=sample_yaml_str),
        APIVerb(verb="GET", full_path="/users", root_path="/users", content=sample_yaml_str),
        APIVerb(verb="POST", full_path="/users", root_path="/users", content=sample_yaml_str),
    ]

    merged = merger.merge(parts_to_merge)

    assert len(merged) == 3

    merged_api_paths = [p for p in merged if isinstance(p, APIPath)]
    merged_api_verbs = [p for p in merged if isinstance(p, APIVerb)]

    assert len(merged_api_paths) == 1
    assert len(merged_api_verbs) == 2

    assert merged_api_paths[0].full_path == "/users"
    assert merged_api_verbs[0].full_path == "/users"
    assert merged_api_verbs[0].verb == "GET"
    assert merged_api_verbs[1].full_path == "/users"
    assert merged_api_verbs[1].verb == "POST"


def test_merger_merge_four_paths_into_two():
    merger = APIDefinitionMerger()

    sample_yaml_str = yaml.dump({"/api/v1/users": {"get": {"description": "user details"}}}, sort_keys=False)

    parts_to_merge = [
        APIPath(full_path="/users/{id}", content=sample_yaml_str),
        APIPath(full_path="/users", content=sample_yaml_str),
        APIVerb(verb="GET", full_path="/users/{id}", root_path="/users", content=sample_yaml_str),
        APIVerb(verb="POST", full_path="/users", root_path="/users", content=sample_yaml_str),
        APIPath(full_path="/orders/{id}", content=sample_yaml_str),
        APIPath(full_path="/orders", content=sample_yaml_str),
        APIVerb(verb="GET", full_path="/orders/{id}", root_path="/orders", content=sample_yaml_str),
        APIVerb(verb="POST", full_path="/orders", root_path="/orders", content=sample_yaml_str),
    ]

    merged = merger.merge(parts_to_merge)

    assert len(merged) == 6

    merged_api_paths = [p for p in merged if isinstance(p, APIPath)]
    merged_api_verbs = [p for p in merged if isinstance(p, APIVerb)]

    assert len(merged_api_paths) == 2
    assert len(merged_api_verbs) == 4

    assert merged_api_paths[0].full_path == "/users"
    assert merged_api_paths[1].full_path == "/orders"


def test_merger_yaml_content_preserved():
    merger = APIDefinitionMerger()

    path_users_details_yaml_str = yaml.dump(
        {"/api/v1/users/{id}": {"get": {"description": "user details"}}}, sort_keys=False
    )
    path_users_list_yaml_str = yaml.dump(
        {"/api/v1/users": {"post": {"description": "create user"}}}, sort_keys=False
    )
    verb_users_get_yaml_str = yaml.dump(
        {"/api/v1/users/{id}": {"get": {"description": "user details"}}}, sort_keys=False
    )
    verb_users_post_yaml_str = yaml.dump(
        {"/api/v1/users": {"post": {"description": "create user"}}}, sort_keys=False
    )

    parts_to_merge = [
        APIPath(full_path="/v1/users/{id}", content=path_users_details_yaml_str),
        APIPath(full_path="/v1/users", content=path_users_list_yaml_str),
        APIVerb(
            verb="GET", full_path="/v1/users/{id}", root_path="/v1/users", content=verb_users_get_yaml_str
        ),
        APIVerb(verb="POST", full_path="/v1/users", root_path="/v1/users", content=verb_users_post_yaml_str),
    ]

    merged = merger.merge(parts_to_merge)

    assert len(merged) == 3

    merged_api_paths = sorted([p for p in merged if isinstance(p, APIPath)], key=lambda x: x.full_path)
    merged_api_verbs = sorted(
        [p for p in merged if isinstance(p, APIVerb)], key=lambda x: (x.full_path, x.verb)
    )

    assert len(merged_api_paths) == 1
    assert len(merged_api_verbs) == 2

    users_path_obj = merged_api_paths[0]
    users_path_yaml_content = yaml.safe_load(users_path_obj.content)

    assert "/api/v1/users/{id}" in users_path_yaml_content
    assert "/api/v1/users" in users_path_yaml_content
    assert len(users_path_yaml_content) == 2
    assert users_path_yaml_content["/api/v1/users/{id}"]["get"]["description"] == "user details"
    assert users_path_yaml_content["/api/v1/users"]["post"]["description"] == "create user"

    assert merged_api_verbs[0].full_path == "/v1/users"
    assert merged_api_verbs[0].verb == "POST"
    assert merged_api_verbs[0].root_path == "/v1/users"
    users_post_verb_yaml = yaml.safe_load(merged_api_verbs[0].content)
    assert users_post_verb_yaml["/api/v1/users"]["post"]["description"] == "create user"

    assert merged_api_verbs[1].full_path == "/v1/users/{id}"
    assert merged_api_verbs[1].verb == "GET"
    assert merged_api_verbs[1].root_path == "/v1/users"
    users_get_verb_yaml = yaml.safe_load(merged_api_verbs[1].content)
    assert users_get_verb_yaml["/api/v1/users/{id}"]["get"]["description"] == "user details"
