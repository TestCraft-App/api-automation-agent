import platform
import subprocess
import pytest
from unittest.mock import patch, MagicMock

from src.utils.system_check import SystemCheck


@pytest.mark.parametrize(
    "platform_system,expected_paths",
    [
        ("Darwin", ["/usr/local/bin/node", "/opt/homebrew/bin/node", "/usr/bin/node", "node"]),
        (
            "Windows",
            ["node", "C:\\Program Files\\nodejs\\node.exe", "C:\\Program Files (x86)\\nodejs\\node.exe"],
        ),
        ("Linux", ["/usr/bin/node", "/usr/local/bin/node", "node"]),
    ],
)
@patch("platform.system")
def test_get_common_node_paths(mock_platform, platform_system, expected_paths):
    mock_platform.return_value = platform_system
    result = SystemCheck.get_common_node_paths()
    assert result == expected_paths


@patch("subprocess.run")
def test_check_nodejs_success_first_path(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "v18.17.0\n"
    mock_run.return_value = mock_result

    with patch.object(SystemCheck, "get_common_node_paths", return_value=["/usr/local/bin/node"]):
        is_installed, version = SystemCheck.check_nodejs()

    assert is_installed is True
    assert version == "v18.17.0"
    mock_run.assert_called_once_with(
        ["/usr/local/bin/node", "--version"], capture_output=True, text=True, timeout=3, shell=False
    )


@patch("subprocess.run")
def test_check_nodejs_success_fallback_shell(mock_run):
    mock_run.side_effect = [
        subprocess.SubprocessError(),
        subprocess.SubprocessError(),
        MagicMock(returncode=0, stdout="v16.20.0\n"),
    ]

    with patch.object(
        SystemCheck, "get_common_node_paths", return_value=["/usr/local/bin/node", "/opt/homebrew/bin/node"]
    ):
        is_installed, version = SystemCheck.check_nodejs()

    assert is_installed is True
    assert version == "v16.20.0"


@patch("subprocess.run")
def test_check_nodejs_not_found(mock_run):
    mock_run.side_effect = [subprocess.SubprocessError(), FileNotFoundError(), OSError(), Exception()]

    with patch.object(SystemCheck, "get_common_node_paths", return_value=["/usr/local/bin/node"]):
        is_installed, version = SystemCheck.check_nodejs()

    assert is_installed is False
    assert version is None


@patch("subprocess.run")
def test_check_nodejs_timeout(mock_run):
    mock_run.side_effect = [subprocess.TimeoutExpired("node", 3), Exception()]

    with patch.object(SystemCheck, "get_common_node_paths", return_value=["/usr/local/bin/node"]):
        is_installed, version = SystemCheck.check_nodejs()

    assert is_installed is False
    assert version is None


@patch("subprocess.run")
def test_check_nodejs_nonzero_exit_code(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_run.side_effect = [mock_result, Exception()]

    with patch.object(SystemCheck, "get_common_node_paths", return_value=["/usr/local/bin/node"]):
        is_installed, version = SystemCheck.check_nodejs()

    assert is_installed is False
    assert version is None


@pytest.mark.parametrize(
    "platform_system,expected_first_path",
    [
        ("Darwin", "/usr/local/bin/npm"),
        ("Windows", "npm"),
        ("Linux", "/usr/bin/npm"),
    ],
)
@patch("subprocess.run")
@patch("platform.system")
def test_check_npm_platform_specific_paths(mock_platform, mock_run, platform_system, expected_first_path):
    mock_platform.return_value = platform_system
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "8.19.2\n"
    mock_run.return_value = mock_result

    is_installed, version = SystemCheck.check_npm()

    assert is_installed is True
    assert version == "8.19.2"
    mock_run.assert_called_once_with(
        [expected_first_path, "--version"], capture_output=True, text=True, timeout=3, shell=False
    )


@patch("subprocess.run")
@patch("platform.system")
def test_check_npm_success_second_path(mock_platform, mock_run):
    mock_platform.return_value = "Windows"
    mock_run.side_effect = [subprocess.SubprocessError(), MagicMock(returncode=0, stdout="9.6.7\n")]

    is_installed, version = SystemCheck.check_npm()

    assert is_installed is True
    assert version == "9.6.7"


@patch("subprocess.run")
@patch("platform.system")
def test_check_npm_fallback_shell_success(mock_platform, mock_run):
    mock_platform.return_value = "Darwin"
    mock_run.side_effect = [
        FileNotFoundError(),
        OSError(),
        subprocess.SubprocessError(),
        subprocess.TimeoutExpired("npm", 3),
        MagicMock(returncode=0, stdout="10.1.0\n"),
    ]

    is_installed, version = SystemCheck.check_npm()

    assert is_installed is True
    assert version == "10.1.0"


@patch("subprocess.run")
@patch("platform.system")
def test_check_npm_not_found(mock_platform, mock_run):
    mock_platform.return_value = "Linux"
    mock_run.side_effect = [subprocess.SubprocessError(), FileNotFoundError(), OSError(), Exception()]

    is_installed, version = SystemCheck.check_npm()

    assert is_installed is False
    assert version is None


@patch("builtins.print")
def test_display_nodejs_warning(mock_print):
    SystemCheck.display_nodejs_warning()

    print_calls = [str(call) for call in mock_print.call_args_list]
    full_output = " ".join(print_calls)

    assert "⚠️  WARNING: Node.js is required but not found!" in full_output
    assert "🚫 This application generates TypeScript API testing frameworks" in full_output
    assert "📥 Please install Node.js before continuing:" in full_output
    assert "https://nodejs.org/" in full_output
    assert "💡 After installation:" in full_output
    assert "node --version" in full_output
    assert "🔧 If Node.js is installed but still not detected:" in full_output
    assert "--skip-system-check" in full_output


@patch("src.utils.system_check.SystemCheck.check_npm")
@patch("src.utils.system_check.SystemCheck.check_nodejs")
@patch("builtins.print")
def test_perform_system_checks_all_pass(mock_print, mock_check_nodejs, mock_check_npm):
    mock_check_nodejs.return_value = (True, "v18.17.0")
    mock_check_npm.return_value = (True, "8.19.2")

    result = SystemCheck.perform_system_checks()

    assert result is True
    print_calls = [str(call) for call in mock_print.call_args_list]
    full_output = " ".join(print_calls)
    assert "✅ Node.js detected: v18.17.0" in full_output
    assert "✅ npm detected: 8.19.2" in full_output


@patch("src.utils.system_check.SystemCheck.display_nodejs_warning")
@patch("src.utils.system_check.SystemCheck.check_npm")
@patch("src.utils.system_check.SystemCheck.check_nodejs")
@patch("builtins.print")
def test_perform_system_checks_nodejs_missing(
    mock_print, mock_check_nodejs, mock_check_npm, mock_display_warning
):
    mock_check_nodejs.return_value = (False, None)
    mock_check_npm.return_value = (True, "8.19.2")

    result = SystemCheck.perform_system_checks()

    assert result is False
    mock_display_warning.assert_called_once()
    print_calls = [str(call) for call in mock_print.call_args_list]
    full_output = " ".join(print_calls)
    assert "💡 If you believe Node.js is installed, you can bypass this check" in full_output
    assert "--skip-system-check" in full_output


@patch("src.utils.system_check.SystemCheck.check_npm")
@patch("src.utils.system_check.SystemCheck.check_nodejs")
@patch("builtins.print")
def test_perform_system_checks_npm_missing(mock_print, mock_check_nodejs, mock_check_npm):
    mock_check_nodejs.return_value = (True, "v18.17.0")
    mock_check_npm.return_value = (False, None)

    result = SystemCheck.perform_system_checks()

    assert result is False
    print_calls = [str(call) for call in mock_print.call_args_list]
    full_output = " ".join(print_calls)
    assert "⚠️  WARNING: npm is required but not found!" in full_output
    assert "🚫 npm (Node Package Manager) is required to install dependencies" in full_output
    assert "💡 npm usually comes with Node.js installation." in full_output
    assert "https://nodejs.org/" in full_output
    assert "🔧 If npm is installed but not detected:" in full_output
    assert "--skip-system-check" in full_output


@patch("src.utils.system_check.SystemCheck.check_npm")
@patch("src.utils.system_check.SystemCheck.check_nodejs")
def test_perform_system_checks_both_missing(mock_check_nodejs, mock_check_npm):
    mock_check_nodejs.return_value = (False, None)
    mock_check_npm.return_value = (False, None)

    result = SystemCheck.perform_system_checks()

    assert result is False


@patch("subprocess.run")
def test_check_nodejs_version_stripping(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "  v20.5.1  \n\r"
    mock_run.return_value = mock_result

    with patch.object(SystemCheck, "get_common_node_paths", return_value=["/usr/local/bin/node"]):
        is_installed, version = SystemCheck.check_nodejs()

    assert is_installed is True
    assert version == "v20.5.1"


@patch("subprocess.run")
@patch("platform.system")
def test_check_npm_version_stripping(mock_platform, mock_run):
    mock_platform.return_value = "Darwin"
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "  10.2.4  \n\r"
    mock_run.return_value = mock_result

    is_installed, version = SystemCheck.check_npm()

    assert is_installed is True
    assert version == "10.2.4"


@patch("subprocess.run")
def test_nodejs_integration_workflow_success(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "v18.17.0\n"
    mock_run.return_value = mock_result

    node_installed, node_version = SystemCheck.check_nodejs()

    assert node_installed is True
    assert node_version == "v18.17.0"
    assert mock_run.call_count >= 1


@patch("subprocess.run")
@patch("platform.system")
def test_npm_integration_workflow_success(mock_platform, mock_run):
    mock_platform.return_value = "Darwin"
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "8.19.2\n"
    mock_run.return_value = mock_result

    npm_installed, npm_version = SystemCheck.check_npm()

    assert npm_installed is True
    assert npm_version == "8.19.2"
    assert mock_run.call_count >= 1
