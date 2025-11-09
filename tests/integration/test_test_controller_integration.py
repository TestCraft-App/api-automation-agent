"""
Integration tests for TestController.
Tests the complete workflow for TypeScript compilation, test execution, and reporting.
"""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from src.configuration.config import Config, Envs
from src.services.command_service import CommandService
from src.test_controller import TestController, TestFileSet, TestRunMetrics


@pytest.mark.integration
class TestTestControllerIntegration:
    """Integration tests for TestController functionality."""

    def setup_method(self):
        """Set up test environment with temporary directory."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.config = Config(
            destination_folder=str(self.test_dir),
            env=Envs.DEV,
        )

        self._create_basic_framework()

    def teardown_method(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _create_basic_framework(self):
        """Create a basic framework structure for testing."""
        package_json = {
            "name": "test-framework",
            "version": "1.0.0",
            "scripts": {"test": "mocha"},
            "devDependencies": {"typescript": "^5.0.0", "mocha": "^10.0.0"},
        }
        (self.test_dir / "package.json").write_text(json.dumps(package_json, indent=2))

        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "ESNext",
                "moduleResolution": "node",
                "strict": True,
            },
            "include": ["src/**/*"],
        }
        (self.test_dir / "tsconfig.json").write_text(json.dumps(tsconfig, indent=2))

        (self.test_dir / "src").mkdir()
        (self.test_dir / "src" / "tests").mkdir()

    def _create_test_file(self, filename: str, content: str, has_error: bool = False):
        """Create a test file with optional TypeScript errors."""
        test_file_path = self.test_dir / "src" / "tests" / filename
        test_file_path.parent.mkdir(parents=True, exist_ok=True)
        test_file_path.write_text(content)
        return str(test_file_path.absolute())

    def test_get_runnable_files_with_no_errors(self):
        """Test that all files are runnable when there are no TypeScript errors."""
        test_file1 = self._create_test_file(
            "test1.spec.ts",
            """
import { expect } from 'chai';

describe('Test Suite 1', () => {
    it('should pass', () => {
        expect(true).to.be.true;
    });
});
""",
        )

        test_file2 = self._create_test_file(
            "test2.spec.ts",
            """
import { expect } from 'chai';

describe('Test Suite 2', () => {
    it('should also pass', () => {
        expect(1 + 1).to.equal(2);
    });
});
""",
        )

        test_files = [{"path": test_file1}, {"path": test_file2}]

        command_service = Mock(spec=CommandService)
        command_service.run_command_silently = Mock(return_value="")

        controller = TestController(self.config, command_service)
        result = controller._get_runnable_files(test_files)

        assert len(result.runnable) == 2
        assert len(result.skipped) == 0
        assert command_service.run_command_silently.called

    def test_get_runnable_files_with_typescript_errors(self):
        """Test that files with TypeScript errors are skipped."""
        test_file1 = self._create_test_file(
            "test_valid.spec.ts",
            """
import { expect } from 'chai';

describe('Valid Test', () => {
    it('should pass', () => {
        expect(true).to.be.true;
    });
});
""",
        )

        test_file2 = self._create_test_file(
            "test_error.spec.ts",
            """
import { expect } from 'chai';

describe('Error Test', () => {
    it('should fail compilation', () => {
        const x: string = 123;  // Type error
    });
});
""",
        )

        test_files = [{"path": test_file1}, {"path": test_file2}]

        def mock_tsc_with_errors(command, cwd=None, env_vars=None):
            if "tsc" in command:
                return (
                    "src/tests/test_error.spec.ts(5,14): error TS2322: "
                    "Type 'number' is not assignable to type 'string'."
                )
            return ""

        command_service = Mock(spec=CommandService)
        command_service.run_command_silently = Mock(side_effect=mock_tsc_with_errors)

        controller = TestController(self.config, command_service)
        result = controller._get_runnable_files(test_files)

        assert (
            "src/tests/test_valid.spec.ts" in result.runnable
            or "src\\tests\\test_valid.spec.ts" in result.runnable
        )
        assert len(result.skipped) == 1

    def test_extract_error_files(self):
        """Test extraction of files with errors from TypeScript compiler output."""
        tsc_output = """
src/tests/test1.spec.ts(10,5): error TS2322: Type 'string' is not assignable to type 'number'.
src/tests/test2.spec.ts(15,10): error TS2304: Cannot find name 'undefined_variable'.
src/models/User.ts(5,3): error TS2339: Property 'nonexistent' does not exist on type 'User'.
"""

        command_service = Mock(spec=CommandService)
        controller = TestController(self.config, command_service)

        error_files = controller._extract_error_files(tsc_output)

        assert len(error_files) == 3
        assert any("test1.spec.ts" in f for f in error_files)
        assert any("test2.spec.ts" in f for f in error_files)
        assert any("User.ts" in f for f in error_files)

    def test_run_tests_flow_with_successful_tests(self):
        """Test the complete test run flow with successful tests."""
        test_file = self._create_test_file(
            "test_success.spec.ts",
            """
import { expect } from 'chai';

describe('Success Test', () => {
    it('should pass test 1', () => {
        expect(true).to.be.true;
    });

    it('should pass test 2', () => {
        expect(1 + 1).to.equal(2);
    });
});
""",
        )

        test_files = [{"path": test_file}]

        command_service = Mock(spec=CommandService)
        command_service.run_command_silently = Mock(return_value="")

        controller = TestController(self.config, command_service)

        mock_tests = [
            {"title": "should pass test 1", "fullTitle": "Success Test should pass test 1", "duration": 10},
            {"title": "should pass test 2", "fullTitle": "Success Test should pass test 2", "duration": 15},
        ]
        mock_failures = []

        with patch.object(controller, "_run_tests", return_value=(mock_tests, mock_failures)):
            result = controller.run_tests_flow(test_files, interactive=False)

        assert result is not None
        assert result.total_tests == 2
        assert result.passed_tests == 2
        assert result.review_tests == 0

    def test_run_tests_flow_with_failed_tests(self):
        """Test the complete test run flow with failed tests."""
        test_file = self._create_test_file(
            "test_failures.spec.ts",
            """
import { expect } from 'chai';

describe('Failure Test', () => {
    it('should pass', () => {
        expect(true).to.be.true;
    });

    it('should fail', () => {
        expect(false).to.be.true;
    });
});
""",
        )

        test_files = [{"path": test_file}]

        command_service = Mock(spec=CommandService)
        command_service.run_command_silently = Mock(return_value="")

        controller = TestController(self.config, command_service)

        mock_tests = [{"title": "should pass", "fullTitle": "Failure Test should pass", "duration": 10}]
        mock_failures = [
            {
                "title": "should fail",
                "fullTitle": "Failure Test should fail",
                "err": {"message": "expected false to be true"},
            }
        ]

        with patch.object(controller, "_run_tests", return_value=(mock_tests, mock_failures)):
            result = controller.run_tests_flow(test_files, interactive=False)

        assert result is not None
        assert result.total_tests == 2
        assert result.passed_tests == 1
        assert result.review_tests == 1

    def test_run_tests_flow_with_skipped_files(self):
        """Test the test run flow when some files have compilation errors."""
        test_file1 = self._create_test_file("test_valid.spec.ts", "")
        test_file2 = self._create_test_file("test_error.spec.ts", "")

        test_files = [{"path": test_file1}, {"path": test_file2}]

        def mock_tsc_output(command, cwd=None, env_vars=None):
            if "tsc" in command:
                return "src/tests/test_error.spec.ts(1,1): error TS1005: ';' expected."
            return ""

        command_service = Mock(spec=CommandService)
        command_service.run_command_silently = Mock(side_effect=mock_tsc_output)

        controller = TestController(self.config, command_service)

        mock_tests = [{"title": "test 1", "fullTitle": "Valid test 1", "duration": 10}]
        mock_failures = []

        with patch.object(controller, "_run_tests", return_value=(mock_tests, mock_failures)):
            result = controller.run_tests_flow(test_files, interactive=False)

        assert result is not None
        assert result.skipped_files == 1
        assert result.total_tests >= 0

    def test_run_tests_flow_interactive_declined(self):
        """Test that test run flow returns None when user declines in interactive mode."""
        test_file = self._create_test_file("test.spec.ts", "")
        test_files = [{"path": test_file}]

        command_service = Mock(spec=CommandService)
        command_service.run_command_silently = Mock(return_value="")

        controller = TestController(self.config, command_service)

        with patch("builtins.input", return_value="n"):
            result = controller.run_tests_flow(test_files, interactive=True)

        assert result is None

    def test_report_tests_groups_by_suite(self):
        """Test that test reporting groups tests by suite correctly."""
        command_service = Mock(spec=CommandService)
        controller = TestController(self.config, command_service)

        tests = [
            {"title": "test 1", "fullTitle": "Suite A test 1", "duration": 10},
            {"title": "test 2", "fullTitle": "Suite A test 2", "duration": 15},
            {"title": "test 1", "fullTitle": "Suite B test 1", "duration": 12},
        ]
        failures = [
            {"title": "test 3", "fullTitle": "Suite A test 3", "err": {"message": "assertion failed"}}
        ]

        report_metrics = controller._report_tests(tests, failures)

        assert report_metrics["total_tests"] == 4
        assert report_metrics["passed_tests"] == 3
        assert report_metrics["review_tests"] == 1

    def test_generate_temp_tsconfig_excludes_error_files(self):
        """Test that temporary tsconfig properly excludes error files."""
        command_service = Mock(spec=CommandService)
        controller = TestController(self.config, command_service)

        error_files = {"src/tests/error1.spec.ts", "src/tests/error2.spec.ts"}

        temp_config_path = controller._generate_temp_tsconfig(error_files)

        assert Path(temp_config_path).exists()

        with open(temp_config_path, "r") as f:
            temp_config = json.load(f)

        assert "exclude" in temp_config
        assert len(temp_config["exclude"]) == 2
        assert any("error1.spec.ts" in f for f in temp_config["exclude"])
        assert any("error2.spec.ts" in f for f in temp_config["exclude"])

        # Clean up
        Path(temp_config_path).unlink()

    def test_test_file_set_structure(self):
        """Test TestFileSet dataclass structure."""
        file_set = TestFileSet(runnable=["test1.ts", "test2.ts"], skipped=["test3.ts"])

        assert len(file_set.runnable) == 2
        assert len(file_set.skipped) == 1
        assert "test1.ts" in file_set.runnable

    def test_test_run_metrics_structure(self):
        """Test TestRunMetrics dataclass structure."""
        metrics = TestRunMetrics(total_tests=10, passed_tests=8, review_tests=2, skipped_files=1)

        assert metrics.total_tests == 10
        assert metrics.passed_tests == 8
        assert metrics.review_tests == 2
        assert metrics.skipped_files == 1

    def test_run_tests_flow_no_runnable_files(self):
        """Test test run flow when all files have compilation errors."""
        test_file = self._create_test_file("test_error.spec.ts", "")
        test_files = [{"path": test_file}]

        def mock_tsc_error(command, cwd=None, env_vars=None):
            return "src/tests/test_error.spec.ts(1,1): error TS1005: ';' expected."

        command_service = Mock(spec=CommandService)
        command_service.run_command_silently = Mock(side_effect=mock_tsc_error)

        controller = TestController(self.config, command_service)
        result = controller.run_tests_flow(test_files, interactive=False)

        assert result is not None
        assert result.total_tests == 0
        assert result.passed_tests == 0
        assert result.review_tests == 0
        assert result.skipped_files == 1
