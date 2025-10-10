from email import message
import logging
from unittest.mock import MagicMock, Mock, patch, call
import subprocess

from src.ai_tools.models.model_file_spec import ModelFileSpec
from src.configuration.config import Config
from src.ai_tools.models.file_spec import FileSpec
from src.services.command_service import CommandService, build_typescript_compiler_command


def test_build_typescript_compiler_command():
    files = [
        FileSpec(path="src/a.ts", fileContent=""),
        FileSpec(path="src/b.ts", fileContent=""),
    ]
    expected = (
        "npx tsc src/a.ts src/b.ts "
        "--lib es2021 "
        "--module NodeNext "
        "--target ESNext "
        "--strict "
        "--esModuleInterop "
        "--skipLibCheck "
        "--forceConsistentCasingInFileNames "
        "--moduleResolution nodenext "
        "--allowUnusedLabels false "
        "--allowUnreachableCode false "
        "--noFallthroughCasesInSwitch "
        "--noImplicitOverride "
        "--noImplicitReturns "
        "--noPropertyAccessFromIndexSignature "
        "--noUncheckedIndexedAccess "
        "--noUnusedLocals "
        "--noUnusedParameters "
        "--checkJs "
        "--noEmit "
        "--strictNullChecks false "
        "--excludeDirectories node_modules"
    )
    assert build_typescript_compiler_command(files) == expected


def test_run_command_with_popen_mock(tmp_path):
    """This test verifies that the CommandService correctly:
    - Executes shell commands using subprocess.Popen
    - Captures and processes command output line by line
    - Properly handles command completion
    - Returns both success status and output in the expected format
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    process_mock = MagicMock()
    process_mock.stdout.readline.side_effect = ["line1\n", "line2\n", ""]
    process_mock.poll.return_value = 0
    process_mock.returncode = 0

    with patch("src.services.command_service.subprocess.Popen", return_value=process_mock) as mock_popen:
        success, output = service.run_command("dummy")
        mock_popen.assert_called_once()

    assert success is True
    assert output == "line1\nline2"


def test_run_command_with_no_stdout(tmp_path):
    """This test verifies that run_command correctly:
    - Handles case when process.stdout is None
    - Logs appropriate error message
    - Returns failure status
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    process_mock = MagicMock()
    process_mock.stdout = None
    process_mock.poll.return_value = 1
    process_mock.returncode = 1

    with patch("src.services.command_service.subprocess.Popen", return_value=process_mock) as mock_popen:
        with patch.object(service, "_log_message") as mock_log:
            success, output = service.run_command("dummy")
            mock_popen.assert_called_once()

            # Verify all log messages in order
            assert mock_log.call_count == 2
            mock_log.assert_has_calls(
                [
                    call("No output stream available.", is_error=True),
                    call("\x1b[91mCommand failed.\x1b[0m", is_error=True),
                ],
            )

    assert success is False
    assert output == ""


def test_run_command_with_subprocess_error(tmp_path):
    """This test verifies that run_command correctly:
    - Handles SubprocessError exceptions
    - Logs appropriate error message
    - Returns failure status
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    with patch(
        "src.services.command_service.subprocess.Popen", side_effect=subprocess.SubprocessError("Test error")
    ):
        success, output = service.run_command("dummy")

    assert success is False
    assert "Test error" in output


def test_run_command_with_general_error(tmp_path):
    """This test verifies that run_command correctly:
    - Handles general exceptions
    - Logs appropriate error message
    - Returns failure status
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    with patch("src.services.command_service.subprocess.Popen", side_effect=Exception("Unexpected error")):
        with patch.object(service, "_log_message") as mock_log:
            success, output = service.run_command("dummy")
            mock_log.assert_called_with("Unexpected error: Unexpected error", is_error=True)

    assert success is False
    assert output == "Unexpected error"


def test_run_command_silently_success(tmp_path):
    """This test verifies that run_command_silently correctly:
    - Executes a command successfully
    - Captures stdout output
    - Returns the output as a string
    - Handles empty stderr appropriately
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    with patch("src.services.command_service.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        output = service.run_command_silently("echo test", cwd=str(tmp_path))
        mock_run.assert_called_once()
        assert output == "test output"


def test_run_command_silently_with_error(tmp_path):
    """This test verifies that run_command_silently correctly:
    - Handles command execution errors
    - Logs error messages from stderr
    - Returns empty string on error
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    with patch("src.services.command_service.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "error message"
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        output = service.run_command_silently("invalid_command", cwd=str(tmp_path))
        mock_run.assert_called_once()
        assert output == ""


def test_run_command_silently_with_env_vars(tmp_path):
    """This test verifies that run_command_silently correctly:
    - Handles custom environment variables
    - Merges them with existing environment variables
    - Passes them to the subprocess
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    custom_env = {"CUSTOM_VAR": "test_value"}

    with patch("src.services.command_service.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        service.run_command_silently("echo test", cwd=str(tmp_path), env_vars=custom_env)

        # Verify that the environment variables were passed correctly
        call_args = mock_run.call_args[1]
        assert "env" in call_args
        assert call_args["env"]["CUSTOM_VAR"] == "test_value"
        # Verify that base environment variables are still present
        assert "PATH" in call_args["env"]


def test_run_command_silently_with_stderr_warning(tmp_path):
    """This test verifies that run_command_silently correctly:
    - Handles stderr output on successful command
    - Logs stderr as debug message
    - Returns stdout output
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    with patch("src.services.command_service.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.stdout = "test output"
        mock_result.stderr = "warning message"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with patch.object(service.logger, "debug") as mock_debug:
            output = service.run_command_silently("echo test", cwd=str(tmp_path))
            mock_run.assert_called_once()
            mock_debug.assert_called_once()
            assert "warning message" in mock_debug.call_args[0][0]
            assert output == "test output"


def test_install_dependencies(tmp_path):
    """This test verifies that install_dependencies correctly:
    - Executes npm install command
    - Returns success status and output
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    with patch.object(service, "run_command") as mock_run:
        mock_run.return_value = (True, "Dependencies installed successfully")
        success, output = service.install_dependencies()

        mock_run.assert_called_once_with("npm install --loglevel=error")
        assert success is True
        assert output == "Dependencies installed successfully"


def test_format_files(tmp_path):
    """This test verifies that format_files correctly:
    - Executes prettify command
    - Returns success status and output
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    with patch.object(service, "run_command") as mock_run:
        mock_run.return_value = (True, "Files formatted successfully")
        success, output = service.format_files()

        mock_run.assert_called_once_with("npm run prettify")
        assert success is True
        assert output == "Files formatted successfully"


def test_run_linter(tmp_path):
    """This test verifies that run_linter correctly:
    - Executes lint:fix command
    - Returns success status and output
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    with patch.object(service, "run_command") as mock_run:
        mock_run.return_value = (True, "Linting completed successfully")
        success, output = service.run_linter()

        mock_run.assert_called_once_with("npm run lint:fix")
        assert success is True
        assert output == "Linting completed successfully"


def test_run_typescript_compiler(tmp_path):
    """This test verifies that run_typescript_compiler correctly:
    - Executes tsc command with noEmit flag
    - Returns success status and output
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    with patch.object(service, "run_command") as mock_run:
        mock_run.return_value = (True, "TypeScript compilation successful")
        success, output = service.run_typescript_compiler()

        mock_run.assert_called_once_with("npx tsc --noEmit")
        assert success is True
        assert output == "TypeScript compilation successful"


def test_get_generated_test_files_empty_directory(tmp_path):
    """This test verifies that get_generated_test_files correctly:
    - Handles non-existent directory
    - Returns empty list when no test files are found
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    test_files = service.get_generated_test_files()
    assert test_files == []


def test_get_generated_test_files_with_tests(tmp_path):
    """This test verifies that get_generated_test_files correctly:
    - Finds test files in the correct directory
    - Filters only .spec.ts files
    - Returns correct file paths
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    test_dir = tmp_path / "src" / "tests"
    test_dir.mkdir(parents=True)
    (test_dir / "test1.spec.ts").touch()
    (test_dir / "test2.spec.ts").touch()
    (test_dir / "not_a_test.txt").touch()

    test_files = service.get_generated_test_files()
    assert len(test_files) == 2
    assert all(file["path"].endswith(".spec.ts") for file in test_files)
    assert any("test1.spec.ts" in file["path"] for file in test_files)
    assert any("test2.spec.ts" in file["path"] for file in test_files)


def test_run_typescript_compiler_for_files(tmp_path):
    """This test verifies that run_typescript_compiler_for_files correctly:
    - Builds correct TypeScript compiler command
    - Executes command for specific files
    - Returns success status and output
    """
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    files = [FileSpec(path="src/test1.ts", fileContent=""), FileSpec(path="src/test2.ts", fileContent="")]

    with patch.object(service, "run_command") as mock_run:
        mock_run.return_value = (True, "TypeScript compilation successful")
        success, output = service.run_typescript_compiler_for_files(files)

        call_args = mock_run.call_args[0][0]
        assert "src/test1.ts" in call_args
        assert "src/test2.ts" in call_args
        assert success is True
        assert output == "TypeScript compilation successful"
