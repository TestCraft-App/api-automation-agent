"""Version checking utility for API Automation Agent.

Handles secure HTTPS requests to GitHub API with proper SSL certificate validation.
Uses certifi for trusted CA certificates in PyInstaller builds.
Supports both SemVer (X.Y.Z) and date-based build versions (build-YYYYMMDD-HHMM).
"""

import json
import os
import re
import ssl
import sys
import urllib.request
from datetime import datetime
from typing import Optional, Tuple

try:
    import certifi
except ImportError:
    certifi = None

from src.version import __version__, __app_name__, GITHUB_REPO_OWNER, GITHUB_REPO_NAME


def _fetch(url: str) -> Optional[dict]:
    """
    Fetch JSON data from URL with proper SSL certificate validation.
    
    Args:
        url: URL to fetch data from
        
    Returns:
        Parsed JSON data if successful, None if failed
    """
    # Create SSL context with proper CA bundle
    ssl_context = None
    try:
        if certifi:
            # Try to use certifi CA bundle
            ca_bundle = certifi.where()
            ssl_context = ssl.create_default_context(cafile=ca_bundle)
        else:
            # Check if bundled CA file exists (PyInstaller)
            if getattr(sys, "_MEIPASS", None):
                bundled_ca = os.path.join(sys._MEIPASS, "certifi", "cacert.pem")
                if os.path.exists(bundled_ca):
                    ssl_context = ssl.create_default_context(cafile=bundled_ca)

            if ssl_context is None:
                ssl_context = ssl.create_default_context()
    except Exception:
        ssl_context = ssl.create_default_context()

    # Create request with User-Agent header
    headers = {"User-Agent": f"{__app_name__}/{__version__} (Python urllib)"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5, context=ssl_context) as response:
            if response.status == 200:
                return json.loads(response.read().decode())
    except Exception:
        pass

    return None


def _normalize_version(tag_name: str) -> str:
    """
    Normalize a GitHub release tag to version string.
    
    Args:
        tag_name: Raw tag name from GitHub API
        
    Returns:
        Normalized version string
    """
    # Handle semantic version tags (v1.2.3 → 1.2.3)
    if tag_name.startswith("v") and re.match(r"v\d+\.\d+\.\d+", tag_name):
        return tag_name[1:]
    
    # Handle date-based build tags (api-automation-agent-build-20250923-1425-main → build-20250923-1425)
    build_match = re.search(r"build-(\d{8}-\d{4})", tag_name)
    if build_match:
        return f"build-{build_match.group(1)}"
    
    # Handle legacy build tags (api-automation-agent-build-25-main → build-25)
    legacy_match = re.search(r"build-(\d+)", tag_name)
    if legacy_match:
        return f"build-{legacy_match.group(1)}"
    
    return tag_name


def _is_build(version: str) -> bool:
    """
    Check if version is a build version.
    
    Args:
        version: Version string to check
        
    Returns:
        True if version is a build version, False otherwise
    """
    return version.startswith("build-")


def _parse_build_dt(version: str) -> Optional[datetime]:
    """
    Parse date-based build version to datetime.
    
    Args:
        version: Build version string (e.g., "build-20250923-1425")
        
    Returns:
        Parsed datetime if valid, None otherwise
    """
    if not _is_build(version):
        return None
    
    # Extract date-time part
    match = re.match(r"build-(\d{8})-(\d{4})", version)
    if not match:
        return None
    
    date_part, time_part = match.groups()
    
    try:
        # Parse YYYYMMDD-HHMM format
        dt_str = f"{date_part}{time_part}"
        return datetime.strptime(dt_str, "%Y%m%d%H%M")
    except ValueError:
        return None


def _parse_semver(version: str) -> Optional[Tuple[int, int, int]]:
    """
    Parse semantic version to tuple.
    
    Args:
        version: Semantic version string (e.g., "1.2.3")
        
    Returns:
        Tuple of (major, minor, patch) if valid, None otherwise
    """
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
    if match:
        return tuple(int(x) for x in match.groups())
    return None


def compare_versions(local_version: str, remote_version: str) -> bool:
    """
    Compare local vs remote version with support for mixed version types.
    
    Args:
        local_version: Current local version
        remote_version: Latest remote version
        
    Returns:
        True if remote version is newer, False otherwise
    """
    local_is_build = _is_build(local_version)
    remote_is_build = _is_build(remote_version)
    
    # Both are date-based builds
    if local_is_build and remote_is_build:
        local_dt = _parse_build_dt(local_version)
        remote_dt = _parse_build_dt(remote_version)
        
        if local_dt and remote_dt:
            return remote_dt > local_dt
        
        # Fallback to legacy build number comparison
        local_match = re.search(r"build-(\d+)$", local_version)
        remote_match = re.search(r"build-(\d+)$", remote_version)
        
        if local_match and remote_match:
            return int(remote_match.group(1)) > int(local_match.group(1))
    
    # Both are semantic versions
    if not local_is_build and not remote_is_build:
        local_semver = _parse_semver(local_version)
        remote_semver = _parse_semver(remote_version)
        
        if local_semver and remote_semver:
            return remote_semver > local_semver
    
    # Mixed types or fallback - use string comparison
    return remote_version != local_version and remote_version > local_version


def get_latest_release_version() -> Optional[str]:
    """
    Fetch the latest release version from GitHub.

    Returns:
        Latest version string if successful, None if failed.
    """
    url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"
    
    data = _fetch(url)
    if not data:
        return None
    
    tag_name = data.get("tag_name", "")
    if not tag_name:
        return None
    
    return _normalize_version(tag_name)

def is_newer_version_available() -> Tuple[bool, Optional[str]]:
    """
    Check if a newer version is available.
    Handles both semantic versions and date-based build tags.

    Returns:
        Tuple of (is_newer_available, latest_version)
    """
    latest_version = get_latest_release_version()

    if not latest_version:
        return False, None

    try:
        is_newer = compare_versions(__version__, latest_version)
        return is_newer, latest_version

    except Exception as e:
        return False, latest_version


def check_for_updates() -> None:
    """
    Check for newer version and print notification if available.
    This is designed to be non-intrusive and won't interrupt the CLI flow.
    """
    try:
        is_newer, latest_version = is_newer_version_available()

        if is_newer and latest_version:
            print(f"")
            print(f"🆕 A newer version ({latest_version}) is available!")
            print(f"   Current version: {__version__}")
            print(f"   Download: https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest")
            print(f"   Consider updating for the latest features and bug fixes.")
            print(f"")
        else:
            print(f"✅ You're running the latest version ({__version__})")

    except Exception as e:
        print(f"⚠️ Version check failed: {e}")
        pass
