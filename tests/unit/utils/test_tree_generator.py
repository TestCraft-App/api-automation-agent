import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "src"))

from utils.tree_generator import FolderStructureGenerator


@pytest.fixture
def mock_project_structure(tmp_path):
    """
    Creates a temporary, realistic file structure for testing.
    tmp_path is a built-in pytest fixture.
    """
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    (project_dir / "src").mkdir()
    (project_dir / "src" / "components").mkdir()
    (project_dir / "src" / "main.py").touch()
    (project_dir / "src" / "components" / "button.js").touch()
    (project_dir / "README.md").touch()

    (project_dir / ".git").mkdir()
    (project_dir / "node_modules").mkdir()
    (project_dir / "dist").mkdir()
    (project_dir / ".env").touch()
    (project_dir / "node_modules" / "some_lib.js").touch()
    (project_dir / "src" / "components" / "deep_folder").mkdir()
    (project_dir / "src" / "components" / "deep_folder" / "deep_file.txt").touch()

    return project_dir


def test_generator_filters_ignored_files(mock_project_structure):
    """Tests that default ignored files/folders are excluded."""
    generator = FolderStructureGenerator()
    output = generator.generate(str(mock_project_structure))

    print(f"Test Filter Output:\n{output}")

    assert ".git" not in output
    assert "node_modules" not in output
    assert ".env" not in output
    assert "__pycache__" not in output
    assert "dist" not in output


def test_generator_respects_max_depth(mock_project_structure):
    """Tests the max_depth limit."""
    generator = FolderStructureGenerator(max_depth=2)
    output = generator.generate(str(mock_project_structure))

    print(f"Test Depth Output:\n{output}")

    assert "src" in output
    assert "components" in output
    assert "button.js" not in output
    assert "deep_folder" not in output
    assert "deep_file.txt" not in output


def test_generator_respects_file_limit(mock_project_structure):
    """Tests the max_files limit."""
    generator = FolderStructureGenerator(max_files=3)
    output = generator.generate(str(mock_project_structure))
    print(f"Test File Limit Output:\n{output}")

    assert "... (limit reached)" in output
    assert "src" in output
    assert "components" in output
    assert "README.md" not in output
    assert "main.py" not in output


def test_generator_is_deterministic(mock_project_structure):
    """Tests that output is the same every time."""
    generator = FolderStructureGenerator()
    output1 = generator.generate(str(mock_project_structure))
    output2 = generator.generate(str(mock_project_structure))
    assert output1 == output2
