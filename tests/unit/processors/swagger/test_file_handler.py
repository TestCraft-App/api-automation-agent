import json
import pytest
from src.processors.swagger.file_handler import FileLoader


def test_file_loader_load_json(tmp_path):
    data = {"key": "value"}
    json_file = tmp_path / "spec.json"
    json_file.write_text(json.dumps(data))
    loader = FileLoader()
    assert loader.load(str(json_file)) == data


def test_file_loader_load_yaml(tmp_path):
    yaml_file = tmp_path / "spec.yaml"
    yaml_file.write_text("key: value\n")
    loader = FileLoader()
    assert loader.load(str(yaml_file)) == {"key": "value"}


def test_file_loader_unsupported_file_format(tmp_path):
    txt_file = tmp_path / "spec.txt"
    txt_file.write_text("just some text")
    loader = FileLoader()
    with pytest.raises(ValueError) as exc:
        loader.load(str(txt_file))
    assert "Unsupported file format" in str(exc.value)


def test_file_loader_file_not_found(tmp_path):
    missing_file = tmp_path / "does_not_exist.yaml"
    loader = FileLoader()
    with pytest.raises(FileNotFoundError):
        loader.load(str(missing_file))


def test_file_loader_invalid_yaml(tmp_path):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("- item1\n - item2: value: another\n::invalid\n")
    loader = FileLoader()
    with pytest.raises(Exception):
        loader.load(str(bad_yaml))


def test_file_loader_invalid_json(tmp_path):
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{invalid json}")
    loader = FileLoader()
    with pytest.raises(json.JSONDecodeError):
        loader.load(str(bad_json))
