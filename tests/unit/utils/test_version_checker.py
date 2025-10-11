import json
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from urllib.error import URLError

from src.utils.version_checker import (
    get_latest_release_version,
    compare_versions,
    is_newer_version_available,
    check_for_updates,
    _normalize_version,
    _is_build,
    _parse_build_dt,
    _parse_semver,
    _fetch,
)


@pytest.mark.parametrize(
    "local_version,remote_version,expected",
    [
        # Legacy build number comparisons
        ("build-10", "build-15", True),
        ("build-15", "build-10", False),
        ("build-15", "build-15", False),
        ("build-1", "build-100", True),
        # Date-based build comparisons
        ("build-20250920-1200", "build-20250920-1300", True),
        ("build-20250920-1300", "build-20250920-1200", False),
        ("build-20250920-1200", "build-20250921-1200", True),
        ("build-20250921-1200", "build-20250920-1200", False),
        ("build-20250920-1200", "build-20250920-1200", False),
        # Semantic version comparisons
        ("1.0.0", "1.1.0", True),
        ("1.1.0", "1.0.0", False),
        ("1.0.0", "1.0.0", False),
        ("1.0.0", "2.0.0", True),
        ("2.0.0", "1.0.0", False),
        ("1.0.0", "1.0.1", True),
        ("1.0.1", "1.0.0", False),
        # Mixed type comparisons (fallback to string comparison)
        ("1.0.0", "build-20250920-1200", True),
        ("build-20250920-1200", "1.5.0", False),
        # Edge cases
        ("", "1.0.0", True),
        ("1.0.0", "", False),
        ("", "", False),
    ],
)
def test_compare_versions(local_version, remote_version, expected):
    result = compare_versions(local_version, remote_version)
    assert result == expected


@pytest.mark.parametrize(
    "tag_name,expected_version",
    [
        # Semantic version tags
        ("v1.2.3", "1.2.3"),
        ("v2.0.0", "2.0.0"),
        # Date-based build tags
        ("api-automation-agent-build-20250920-1200-main", "build-20250920-1200"),
        ("api-automation-agent-build-20250923-1425-agent-cli", "build-20250923-1425"),
        # Legacy build tags
        ("api-automation-agent-build-15-main", "build-15"),
        ("api-automation-agent-build-100-agent-cli", "build-100"),
        ("build-25", "build-25"),
        # Other formats
        ("1.0.0", "1.0.0"),
        ("release-v1.0.0", "release-v1.0.0"),
        ("beta-build-10", "build-10"),
    ],
)
@patch("urllib.request.urlopen")
def test_get_latest_release_version_parsing(mock_urlopen, tag_name, expected_version):
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.status = 200
    mock_response.read.return_value.decode.return_value = json.dumps({"tag_name": tag_name})

    result = get_latest_release_version()
    assert result == expected_version


@patch("urllib.request.urlopen")
def test_get_latest_release_version_api_failure(mock_urlopen):
    mock_urlopen.side_effect = URLError("Network error")
    result = get_latest_release_version()
    assert result is None


@patch("urllib.request.urlopen")
def test_get_latest_release_version_http_error(mock_urlopen):
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.status = 404
    result = get_latest_release_version()
    assert result is None


@patch("urllib.request.urlopen")
def test_get_latest_release_version_malformed_json(mock_urlopen):
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.status = 200
    mock_response.read.return_value.decode.return_value = "invalid json"
    result = get_latest_release_version()
    assert result is None


@patch("urllib.request.urlopen")
def test_get_latest_release_version_missing_tag_name(mock_urlopen):
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.status = 200
    mock_response.read.return_value.decode.return_value = json.dumps({})
    result = get_latest_release_version()
    assert result is None


@patch("urllib.request.urlopen")
def test_get_latest_release_version_correct_url(mock_urlopen):
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.status = 200
    mock_response.read.return_value.decode.return_value = json.dumps({"tag_name": "v1.0.0"})

    get_latest_release_version()

    # Verify the call was made with a Request object, timeout, and SSL context
    mock_urlopen.assert_called_once()
    call_args = mock_urlopen.call_args

    # Check that first argument is a Request object with correct URL
    request_obj = call_args[0][0]
    assert hasattr(request_obj, "full_url")
    assert (
        request_obj.full_url
        == "https://api.github.com/repos/TestCraft-App/api-automation-agent/releases/latest"
    )

    # Check that timeout and context are provided
    assert call_args[1]["timeout"] == 5
    assert "context" in call_args[1]


@patch("src.utils.version_checker.__version__", "1.0.0")
@patch("src.utils.version_checker.get_latest_release_version")
def test_is_newer_version_available_true(mock_get_latest):
    mock_get_latest.return_value = "build-25"

    is_newer, latest = is_newer_version_available()

    assert is_newer is True
    assert latest == "build-25"


@patch("src.utils.version_checker.__version__", "build-25")
@patch("src.utils.version_checker.get_latest_release_version")
def test_is_newer_version_available_false(mock_get_latest):
    mock_get_latest.return_value = "build-20"

    is_newer, latest = is_newer_version_available()

    assert is_newer is False
    assert latest == "build-20"


@patch("src.utils.version_checker.__version__", "1.0.0")
@patch("src.utils.version_checker.get_latest_release_version")
def test_is_newer_version_available_api_failure(mock_get_latest):
    mock_get_latest.return_value = None

    is_newer, latest = is_newer_version_available()

    assert is_newer is False
    assert latest is None


@patch("src.utils.version_checker.__version__", "1.0.0")
@patch("src.utils.version_checker.is_newer_version_available")
@patch("builtins.print")
def test_check_for_updates_newer_available(mock_print, mock_is_newer):
    mock_is_newer.return_value = (True, "build-25")

    check_for_updates()

    print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
    assert any("🆕 A newer version (build-25) is available!" in call for call in print_calls)
    assert any("Current version: 1.0.0" in call for call in print_calls)


@patch("src.utils.version_checker.__version__", "build-25")
@patch("src.utils.version_checker.is_newer_version_available")
@patch("builtins.print")
def test_check_for_updates_up_to_date(mock_print, mock_is_newer):
    mock_is_newer.return_value = (False, "build-20")

    check_for_updates()

    print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
    assert any("✅ You're running the latest version (build-25)" in call for call in print_calls)


@patch("src.utils.version_checker.is_newer_version_available")
@patch("builtins.print")
def test_check_for_updates_exception_handling(mock_print, mock_is_newer):
    mock_is_newer.side_effect = Exception("Test error")

    check_for_updates()

    print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
    assert any("⚠️ Version check failed:" in call for call in print_calls)


@patch("urllib.request.urlopen")
@patch("src.utils.version_checker.__version__", "build-10")
def test_integration_newer_version_workflow(mock_urlopen):
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.status = 200
    mock_response.read.return_value.decode.return_value = json.dumps(
        {"tag_name": "api-automation-agent-build-15-main"}
    )

    is_newer, latest = is_newer_version_available()

    assert is_newer is True
    assert latest == "build-15"


@patch("urllib.request.urlopen")
@patch("src.utils.version_checker.__version__", "build-20")
def test_integration_up_to_date_workflow(mock_urlopen):
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.status = 200
    mock_response.read.return_value.decode.return_value = json.dumps({"tag_name": "v1.0.0"})

    is_newer, latest = is_newer_version_available()

    assert is_newer is False
    assert latest == "1.0.0"


# Tests for helper functions
@pytest.mark.parametrize(
    "tag_name,expected",
    [
        ("v1.2.3", "1.2.3"),
        ("v10.0.1", "10.0.1"),
        ("api-automation-agent-build-20250920-1200-main", "build-20250920-1200"),
        ("api-automation-agent-build-20250923-1425-agent-cli", "build-20250923-1425"),
        ("api-automation-agent-build-15-main", "build-15"),
        ("build-25", "build-25"),
        ("random-tag", "random-tag"),
        ("", ""),
    ],
)
def test_normalize_version(tag_name, expected):
    result = _normalize_version(tag_name)
    assert result == expected


@pytest.mark.parametrize(
    "version,expected",
    [
        ("build-20250920-1200", True),
        ("build-15", True),
        ("1.2.3", False),
        ("v1.2.3", False),
        ("", False),
        ("random", False),
    ],
)
def test_is_build(version, expected):
    result = _is_build(version)
    assert result == expected


@pytest.mark.parametrize(
    "version,expected_dt",
    [
        ("build-20250920-1200", datetime(2025, 9, 20, 12, 0)),
        ("build-20250923-1425", datetime(2025, 9, 23, 14, 25)),
        ("build-20250101-0000", datetime(2025, 1, 1, 0, 0)),
        ("build-20251231-2359", datetime(2025, 12, 31, 23, 59)),
        ("build-15", None),  # Legacy format
        ("1.2.3", None),  # Not a build version
        ("build-invalid", None),  # Invalid format
        ("", None),  # Empty string
    ],
)
def test_parse_build_dt(version, expected_dt):
    result = _parse_build_dt(version)
    assert result == expected_dt


@pytest.mark.parametrize(
    "version,expected",
    [
        ("1.2.3", (1, 2, 3)),
        ("10.0.1", (10, 0, 1)),
        ("0.0.0", (0, 0, 0)),
        ("999.999.999", (999, 999, 999)),
        ("1.2", None),  # Invalid format
        ("1.2.3.4", None),  # Too many parts
        ("v1.2.3", None),  # Has prefix
        ("build-15", None),  # Not semver
        ("", None),  # Empty string
        ("1.2.a", None),  # Non-numeric
    ],
)
def test_parse_semver(version, expected):
    result = _parse_semver(version)
    assert result == expected


@patch("urllib.request.urlopen")
def test_fetch_success(mock_urlopen):
    expected_data = {"tag_name": "v1.0.0"}
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.status = 200
    mock_response.read.return_value.decode.return_value = json.dumps(expected_data)

    result = _fetch("https://api.github.com/test")
    assert result == expected_data


@patch("urllib.request.urlopen")
def test_fetch_network_error(mock_urlopen):
    mock_urlopen.side_effect = URLError("Network error")

    result = _fetch("https://api.github.com/test")
    assert result is None


@patch("urllib.request.urlopen")
def test_fetch_http_error(mock_urlopen):
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.status = 404

    result = _fetch("https://api.github.com/test")
    assert result is None


@patch("urllib.request.urlopen")
def test_fetch_invalid_json(mock_urlopen):
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.status = 200
    mock_response.read.return_value.decode.return_value = "invalid json"

    result = _fetch("https://api.github.com/test")
    assert result is None
