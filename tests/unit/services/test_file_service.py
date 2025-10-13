import os
import sys
from pathlib import Path
import pytest
from src.services.file_service import FileService, get_resource_path
from src.exceptions import FrameworkTemplateCopyError
from src.ai_tools.models.file_spec import FileSpec


def test_file_service_create_files(tmp_path):
    fs = FileService()
    files = [FileSpec(path="dir/a.txt", fileContent="hello"), FileSpec(path="b.txt", fileContent="world")]
    created = fs.create_files(str(tmp_path), files)
    expected_paths = [tmp_path / "dir" / "a.txt", tmp_path / "b.txt"]
    # Normalize to same absolute path objects to avoid slash direction differences
    assert {Path(p).resolve() for p in created} == {p.resolve() for p in expected_paths}
    for p in expected_paths:
        assert p.exists()


def test_file_service_read_file(tmp_path):
    path = tmp_path / "readme.txt"
    content = "sample text"
    path.write_text(content)
    fs = FileService()
    assert fs.read_file(str(path)) == content


def test_file_service_read_file_missing():
    fs = FileService()
    assert fs.read_file("nonexistent_file_12345.txt") is None


def test_copy_framework_template_success(tmp_path):
    fs = FileService()
    dest_dir = tmp_path / "new-framework"
    dest_dir.mkdir()
    result = fs.copy_framework_template(str(dest_dir))
    assert result == str(dest_dir)
    assert (dest_dir / "package.json").exists()
    assert (dest_dir / "src").is_dir()


def test_copy_framework_template_failure(tmp_path, monkeypatch):
    fs = FileService()
    dest_dir = tmp_path / "bad-framework"
    dest_dir.mkdir()

    def boom(*args, **kwargs):  # noqa: D401
        raise OSError("copy failure")

    monkeypatch.setattr("shutil.copytree", boom)
    with pytest.raises(FrameworkTemplateCopyError) as exc:
        fs.copy_framework_template(str(dest_dir))
    assert "copy failure" in str(exc.value)


def test_create_files_edge_cases(tmp_path):
    fs = FileService()
    files = [
        # Quoted content that should be unwrapped via ast.literal_eval
        FileSpec(path="quoted.txt", fileContent='"line1\\nline2"'),
        # Starts with ./ should be trimmed
        FileSpec(path="./relative/trim.txt", fileContent="data"),
        # Leading slash should be stripped
        FileSpec(path="/leading/slash.txt", fileContent="rooted"),
    ]
    created_paths = fs.create_files(str(tmp_path), files)

    # Validate returned paths correspond to actual filesystem
    expected_relatives = [
        "quoted.txt",
        os.path.join("relative", "trim.txt"),
        os.path.join("leading", "slash.txt"),
    ]
    assert sorted(Path(p).relative_to(tmp_path).as_posix() for p in created_paths) == sorted(
        p.replace(os.sep, "/") for p in expected_relatives
    )

    # Confirm newline un-escaped
    quoted_contents = (tmp_path / "quoted.txt").read_text()
    assert quoted_contents == "line1\nline2"


def test_get_resource_path_pyinstaller(monkeypatch, tmp_path):
    # Simulate PyInstaller _MEIPASS attribute
    fake_meipass = tmp_path / "_MEIPASS"
    fake_meipass.mkdir()
    monkeypatch.setattr(sys, "_MEIPASS", str(fake_meipass), raising=False)
    rel = "some/rel/path.txt"
    result = get_resource_path(rel)
    assert result == os.path.join(str(fake_meipass), rel)


def test_get_resource_path_fallback():
    # Ensure _MEIPASS missing
    if hasattr(sys, "_MEIPASS"):
        delattr(sys, "_MEIPASS")
    rel = "another/thing"
    result = get_resource_path(rel)
    assert result.endswith(os.path.join(os.getcwd(), rel))
