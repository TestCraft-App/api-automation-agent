import os
import subprocess
import logging
from typing import List, Dict, Tuple, Optional, Callable

from ..configuration.config import Config


class CommandService:
    """
    Service for running shell commands with real-time output and error handling.
    """

    def __init__(self, config: Config, logger: Optional[logging.Logger] = None):
        """
        Initialize CommandService with an optional logger.

        Args:
            config (Config): Configuration instance
            logger (Optional[logging.Logger]): Logger instance (defaults to logger from logging module)
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def _log_message(self, message: str, is_error: bool = False):
        """
        Log a message with optional error severity.

        Args:
            message (str): Message to log
            is_error (bool): Whether the message is an error
        """
        log_method = self.logger.error if is_error else self.logger.info
        log_method(message)

    def run_command(self, command: str, cwd: Optional[str] = None) -> Tuple[bool, str]:
        """
        Run a shell command with real-time output and error handling.

        Args:
            command (str): Command to execute
            cwd (Optional[str]): Working directory for command execution

        Returns:
            Tuple[bool, str]: Success status and command output
        """
        try:
            self.logger.info(f"Running command: {command}")
            process = subprocess.Popen(
                command,
                cwd=cwd or self.config.destination_folder,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                universal_newlines=True,
                encoding="utf-8",
                env={
                    **os.environ,
                    "PYTHONUNBUFFERED": "1",
                    "FORCE_COLOR": "true",
                    "TERM": "xterm-256color",
                    "LANG": "en_US.UTF-8",
                    "LC_ALL": "en_US.UTF-8",
                },
            )

            output_lines = []
            while True:
                output = process.stdout.readline()
                if output:
                    output_lines.append(output.rstrip())
                    self._log_message(output.rstrip())

                if output == "" and process.poll() is not None:
                    break

            success = process.returncode == 0
            self._log_message(
                (
                    f"\033[92mCommand succeeded.\033[0m"
                    if success
                    else f"\033[91mCommand failed.\033[0m"
                ),
                is_error=not success,
            )
            return success, "\n".join(output_lines)

        except subprocess.SubprocessError as e:
            self._log_message(f"Subprocess error: {e}", is_error=True)
            return False, str(e)
        except Exception as e:
            self._log_message(f"Unexpected error: {e}", is_error=True)
            return False, str(e)

    def run_command_with_fix(
        self,
        command_func: Callable,
        fix_func: Optional[Callable] = None,
        files: Optional[List[Dict[str, str]]] = None,
        max_retries: int = 3,
    ) -> Tuple[bool, str]:
        """
        Execute a command with retries and an optional fix function on failure.

        Args:
            command_func (Callable): The function that runs the command
            fix_func (Optional[Callable]): Function to invoke if the command fails
            files (Optional[List[Dict[str, str]]]): Files to pass to the command function
            max_retries (int): Max number of retries on failure

        Returns:
            Tuple[bool, str]: Success status and output or error message
        """
        files = files or []
        retry_count = 0
        while retry_count < max_retries:
            if retry_count > 0:
                self._log_message(f"\nAttempt {retry_count + 1}/{max_retries}.")
            elif retry_count == 0:
                self._log_message("")

            success, message = command_func(files)

            if success:
                return success, message

            if fix_func:
                self._log_message(f"Applying fix: {message}")
                fix_func(files, message)

            retry_count += 1

        self._log_message(
            f"Command failed after {max_retries} attempts.", is_error=True
        )
        return command_func(files)

    def install_dependencies(self) -> Tuple[bool, str]:
        """Install npm dependencies"""
        self._log_message("\nInstalling dependencies...")
        return self.run_command("npm install --loglevel=error")

    def format_files(self) -> Tuple[bool, str]:
        """Format the generated files"""
        self._log_message("\nFormatting files...")
        return self.run_command("npm run prettify")

    def run_linter(self) -> Tuple[bool, str]:
        """Run the linter with auto-fix"""
        self._log_message("\nRunning linter...")
        return self.run_command("npm run lint:fix")

    def run_typescript_compiler(self) -> Tuple[bool, str]:
        """Run the TypeScript compiler"""
        self._log_message("\nRunning TypeScript compiler...")
        return self.run_command("npx tsc --noEmit")

    def run_typescript_compiler_for_files(
        self,
        files: List[Dict[str, str]],
    ) -> Tuple[bool, str]:
        """Run TypeScript compiler for specific files"""
        self._log_message(
            f"Running TypeScript compiler for files: {[file['path'] for file in files]}"
        )
        compiler_command = build_typescript_compiler_command(files)
        return self.run_command(compiler_command)

    def run_tests(self) -> Tuple[bool, str]:
        """Run all tests"""
        self._log_message("\nRunning tests...")
        return self.run_command("npm run test")

    def run_specific_test(self, files: List[Dict[str, str]]) -> Tuple[bool, str]:
        """Run specific tests"""
        file_paths = " ".join(file["path"] for file in files)
        self._log_message(f"\nRunning tests: {file_paths}")
        return self.run_command(f"mocha {file_paths} --timeout 10000")


def build_typescript_compiler_command(files: List[Dict[str, str]]) -> str:
    """Build the TypeScript compiler command for specific files"""
    file_paths = " ".join(file["path"] for file in files)
    return (
        f"npx tsc {file_paths} "
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
        "--exactOptionalPropertyTypes "
        "--noFallthroughCasesInSwitch "
        "--noImplicitOverride "
        "--noImplicitReturns "
        "--noPropertyAccessFromIndexSignature "
        "--noUncheckedIndexedAccess "
        "--noUnusedLocals "
        "--noUnusedParameters "
        "--checkJs "
        "--noEmit"
    )
