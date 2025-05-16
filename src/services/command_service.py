import logging
import os
import subprocess
from typing import List, Dict, Tuple, Optional, Callable

from ..ai_tools.models.file_spec import FileSpec
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
                if process.stdout is None:
                    self._log_message("No output stream available.", is_error=True)
                    break
                output = process.stdout.readline()
                if output:
                    output_lines.append(output.rstrip())
                    self._log_message(output.rstrip())

                if output == "" and process.poll() is not None:
                    break

            success = process.returncode == 0
            self._log_message(
                ("\033[92mCommand succeeded.\033[0m" if success else "\033[91mCommand failed.\033[0m"),
                is_error=not success,
            )
            return success, "\n".join(output_lines)

        except subprocess.SubprocessError as e:
            self._log_message(f"Subprocess error: {e}", is_error=True)
            return False, str(e)
        except Exception as e:
            self._log_message(f"Unexpected error: {e}", is_error=True)
            return False, str(e)

    def run_command_silently(self, command: str, cwd: str, env_vars: Optional[Dict[str, str]] = None) -> str:
        """Run a command silently, capturing stdout and stderr.

        Args:
            command (str): The command to run.
            cwd (str): The working directory.
            env_vars (Optional[Dict[str, str]]): Additional environment variables to set/override.

        Returns:
            str: The stdout of the command, or empty string if none.
        """
        process_env = os.environ.copy()
        if env_vars:
            process_env.update(env_vars)

        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            env=process_env,  # Pass the combined environment
        )
        # Log stderr if there was an error or if it contains anything interesting
        if result.returncode != 0 and result.stderr:
            self.logger.error(f"Command '{command}' failed with stderr:\n{result.stderr}")
        elif result.stderr:  # Log stderr even on success if it's not empty, as it might contain warnings
            self.logger.debug(f"Command '{command}' produced stderr (even if successful):\n{result.stderr}")

        return result.stdout or ""

    def run_command_with_fix(
        self,
        command_func: Callable,
        fix_func: Optional[Callable] = None,
        files: Optional[List[FileSpec]] = None,
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

        success, message = command_func(files)

        if success:
            return success, message

        self._log_message(f"Command failed after {max_retries} attempts.", is_error=True)
        return False, message

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
        self._log_message("\nRunning TypeScript compiler...\n")
        return self.run_command("npx tsc --noEmit")

    def get_generated_test_files(self) -> List[Dict[str, str]]:
        """Find and return a list of all generated test files from the correct destination folder."""

        test_dir = os.path.join(self.config.destination_folder, "src", "tests")
        test_files = []

        if not os.path.exists(test_dir):
            self._log_message(
                f"⚠️ Test directory '{test_dir}' does not exist. No tests found.",
                is_error=True,
            )
            return []

        for root, _, files in os.walk(test_dir):
            for file in files:
                if file.endswith(".spec.ts"):
                    test_files.append({"path": os.path.join(root, file)})

        return test_files

    def run_typescript_compiler_for_files(
        self,
        files: List[FileSpec],
    ) -> Tuple[bool, str]:
        """Run TypeScript compiler for specific files"""
        self._log_message(f"Running TypeScript compiler for files: {[file.path for file in files]}")
        compiler_command = build_typescript_compiler_command(files)
        return self.run_command(compiler_command)


def build_typescript_compiler_command(files: List[FileSpec]) -> str:
    """Build the TypeScript compiler command for specific files"""
    file_paths = " ".join(file.path for file in files)
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
