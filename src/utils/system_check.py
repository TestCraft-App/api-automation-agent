import subprocess
import sys
import os
import platform
from typing import Tuple, Optional


class SystemCheck:
    """Utility class for checking system requirements."""

    @staticmethod
    def get_common_node_paths():
        """Get common Node.js installation paths for different platforms."""
        if platform.system() == "Darwin":
            return [
                "/usr/local/bin/node",
                "/opt/homebrew/bin/node",
                "/usr/bin/node",
                "node",
            ]
        elif platform.system() == "Windows":
            return [
                "node",
                "C:\\Program Files\\nodejs\\node.exe",
                "C:\\Program Files (x86)\\nodejs\\node.exe",
            ]
        else:
            return ["/usr/bin/node", "/usr/local/bin/node", "node"]

    @staticmethod
    def check_nodejs() -> Tuple[bool, Optional[str]]:
        """
        Check if Node.js is installed and accessible.

        Returns:
            Tuple[bool, Optional[str]]: (is_installed, version_or_none)
        """
        node_paths = SystemCheck.get_common_node_paths()

        for node_path in node_paths:
            try:
                result = subprocess.run(
                    [node_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    shell=False,
                )

                if result.returncode == 0:
                    version = result.stdout.strip()
                    return True, version

            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError, OSError):
                continue

        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=3, shell=True
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
        except:
            pass

        return False, None

    @staticmethod
    def check_npm() -> Tuple[bool, Optional[str]]:
        """
        Check if npm is installed and accessible.

        Returns:
            Tuple[bool, Optional[str]]: (is_installed, version_or_none)
        """
        if platform.system() == "Darwin":
            npm_paths = ["/usr/local/bin/npm", "/opt/homebrew/bin/npm", "/usr/bin/npm", "npm"]
        elif platform.system() == "Windows":
            npm_paths = [
                "npm",
                "C:\\Program Files\\nodejs\\npm.cmd",
                "C:\\Program Files (x86)\\nodejs\\npm.cmd",
            ]
        else:
            npm_paths = ["/usr/bin/npm", "/usr/local/bin/npm", "npm"]

        for npm_path in npm_paths:
            try:
                result = subprocess.run(
                    [npm_path, "--version"], capture_output=True, text=True, timeout=3, shell=False
                )

                if result.returncode == 0:
                    version = result.stdout.strip()
                    return True, version

            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError, OSError):
                continue

        try:
            result = subprocess.run(
                ["npm", "--version"], capture_output=True, text=True, timeout=3, shell=True
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
        except:
            pass

        return False, None

    @staticmethod
    def display_nodejs_warning():
        """Display a warning message about missing Node.js."""
        print("\n" + "=" * 70)
        print("⚠️  WARNING: Node.js is required but not found!")
        print("=" * 70)
        print("🚫 This application generates TypeScript API testing frameworks")
        print("   that require Node.js and npm to function properly.")
        print()
        print("📥 Please install Node.js before continuing:")
        print("   • Download from: https://nodejs.org/")
        print("   • Recommended: Latest LTS version")
        print()
        print("💡 After installation:")
        print("   1. Restart your terminal/command prompt")
        print("   2. Verify installation: node --version")
        print("   3. Run this application again")
        print()
        print("🔧 If Node.js is installed but still not detected:")
        print("   • Try running with: --skip-system-check")
        print("   • This may occur with PyInstaller executables on some systems")
        print("=" * 70)
        print()

    @staticmethod
    def perform_system_checks() -> bool:
        """
        Perform all system requirement checks.

        Returns:
            bool: True if all requirements are met, False otherwise
        """
        node_installed, node_version = SystemCheck.check_nodejs()
        npm_installed, npm_version = SystemCheck.check_npm()

        if not node_installed:
            SystemCheck.display_nodejs_warning()
            print("💡 If you believe Node.js is installed, you can bypass this check")
            print("   by running with the --skip-system-check flag")
            return False

        if not npm_installed:
            print("\n" + "=" * 70)
            print("⚠️  WARNING: npm is required but not found!")
            print("=" * 70)
            print("🚫 npm (Node Package Manager) is required to install dependencies")
            print("   and run the generated TypeScript testing framework.")
            print()
            print("💡 npm usually comes with Node.js installation.")
            print("   If Node.js is installed but npm is missing:")
            print("   • Reinstall Node.js from https://nodejs.org/")
            print("   • Or install npm separately")
            print()
            print("🔧 If npm is installed but not detected:")
            print("   • Try running with: --skip-system-check")
            print("=" * 70)
            print()
            return False

        print(f"✅ Node.js detected: {node_version}")
        print(f"✅ npm detected: {npm_version}")
        print()

        return True
