from src.models.api_verb import APIVerb


def test_api_verb_instantiation():
    """Test that APIVerb instances are created with the correct values."""
    path = "/test/path"
    yaml_content = "test: content"
    verb = "GET"
    root_path = "/test"

    api_verb = APIVerb(full_path=path, content=yaml_content, verb=verb, root_path=root_path)

    assert api_verb.type == "verb"
    assert api_verb.full_path == path
    assert api_verb.content == yaml_content
    assert api_verb.verb == verb
    assert api_verb.root_path == root_path


def test_api_verb_to_json():
    """Test that APIVerb instances are correctly converted to JSON."""
    path = "/test/path"
    yaml_content = "test: content"
    verb = "GET"
    root_path = "/test"

    api_verb = APIVerb(full_path=path, content=yaml_content, verb=verb, root_path=root_path)

    json_data = api_verb.to_json()
    assert json_data == {
        "verb": verb,
        "path": path,
        "root_path": root_path,
        "yaml": yaml_content,
        "type": "verb",
    }
