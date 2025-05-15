import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set

from json_repair import repair_json

from src.configuration.config import Config
from src.services.command_service import CommandService
from src.utils.logger import Logger
from src.visuals.loading_animator import LoadingDotsAnimator


@dataclass
class TestFileSet:
    runnable: List[str]
    skipped: List[str]


@dataclass
class TestRunMetrics:
    total_tests: int
    passed_tests: int
    review_tests: int
    skipped_files: int


class TestController:
    def __init__(self, config: Config, command_service: CommandService):
        self.command_service = command_service
        self.config = config
        self.logger = Logger.get_logger(__name__)

    def _get_runnable_files(self, test_files: List[Dict[str, str]]) -> TestFileSet:
        self.logger.info("\n🧪 Starting TypeScript compilation to find errors...\n")

        root = Path(self.config.destination_folder).resolve()
        test_file_paths_set = {
            str(Path(f["path"]).resolve().relative_to(root)).replace("\\", "/") for f in test_files
        }

        try:
            tsc_output = self.command_service.run_command_silently(
                "npx tsc --noEmit", cwd=self.config.destination_folder
            )
        except subprocess.CalledProcessError as e:
            tsc_output = e.output or ""

        all_error_files = self._extract_error_files(tsc_output)

        if not all_error_files:
            runnable_files = list(test_file_paths_set)
            self.logger.info("✅ No errors found in compilation, continuing normally.\n")

            self.logger.info("✅ Test files ready to run:")
            for path in runnable_files:
                self.logger.info(f"   - {path}")
            return TestFileSet(runnable=runnable_files, skipped=[])

        temp_tsconfig_path = self._generate_temp_tsconfig(all_error_files)

        try:
            for _ in range(self.config.tsc_max_passes):
                try:
                    new_output = self.command_service.run_command_silently(
                        f"npx tsc --noEmit --project {temp_tsconfig_path}",
                        cwd=self.config.destination_folder,
                    )
                except subprocess.CalledProcessError as e:
                    new_output = e.output or ""

                new_error_files = self._extract_error_files(new_output)
                newly_discovered = new_error_files - all_error_files

                if not newly_discovered:
                    break

                all_error_files.update(newly_discovered)

                with open(temp_tsconfig_path, "r", encoding="utf-8") as f:
                    temp_config = json.load(f)

                for err in newly_discovered:
                    if err not in temp_config["exclude"]:
                        temp_config["exclude"].append(err)

                with open(temp_tsconfig_path, "w", encoding="utf-8") as f:
                    json.dump(temp_config, f, indent=2)

            runnable_files = []
            skipped_files = []

            for test_file in test_file_paths_set:
                if test_file in all_error_files:
                    skipped_files.append(test_file)
                else:
                    runnable_files.append(test_file)

            if runnable_files:
                self.logger.info("\n✅ Test files ready to run:")
                for path in runnable_files:
                    self.logger.info(f"   - {path}")
            else:
                self.logger.warning("\n⚠️ No test files can be run due to compilation errors.")

            if skipped_files:
                self.logger.warning("\n❌ Skipping test files with TypeScript compilation errors:")
                for path in skipped_files:
                    self.logger.warning(f"   - {path}")

            self.logger.info("\nFinal checks completed")
            return TestFileSet(runnable=runnable_files, skipped=skipped_files)
        finally:
            temp_file = Path(temp_tsconfig_path)
            if temp_file.exists():
                temp_file.unlink()
                self.logger.debug(f"Deleted temporary tsconfig file: {temp_tsconfig_path}")

    def _extract_error_files(self, tsc_output: str) -> Set[str]:
        error_files = set()
        root = Path(self.config.destination_folder).resolve()

        for line in tsc_output.splitlines():
            match = re.search(r"(.*?\.(ts|js))\(\d+,\d+\):", line.replace("\\", "/"))
            if match:
                raw_path = match.group(1)
                full_path = (root / raw_path).resolve()
                rel_path = str(full_path.relative_to(root))
                normalized = Path(rel_path).as_posix()
                error_files.add(normalized)

        return error_files

    def _generate_temp_tsconfig(self, excluded_files: Set[str]) -> str:
        tsconfig_path = Path(self.config.destination_folder).resolve() / "tsconfig.json"

        with open(tsconfig_path, "r", encoding="utf-8") as f:
            base_tsconfig = json.load(f)

        exclude = []
        for file_path in excluded_files:
            exclude.append(file_path)

        includes = base_tsconfig.get("include", ["src/**/*"])

        temp_config = {
            "compilerOptions": base_tsconfig.get("compilerOptions", {}),
            "include": includes,
            "exclude": exclude,
        }

        temp_file_path = Path(self.config.destination_folder).resolve() / "temp_tsconfig.json"

        with open(temp_file_path, "w", encoding="utf-8") as f:
            json.dump(temp_config, f, indent=2)

        return str(temp_file_path)

    @staticmethod
    def _prompt_to_run_tests(interactive: bool = True) -> bool:
        if not interactive:
            return True
        answer = input("\n🧪 Do you want to run the tests now? (y/n): ").strip().lower()
        return answer in ("y", "yes")

    def _run_tests(
        self, test_files: List[str], skipped_files: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        if skipped_files is None:
            skipped_files = []
        self.logger.info("\n🛠️ Running tests ...\n")
        all_parsed_tests = []
        all_parsed_failures = []

        total_files = len(test_files)

        for index, test_file in enumerate(test_files, start=1):
            file_name = Path(test_file).name
            stdout = ""
            repaired_json_string = None

            animator = LoadingDotsAnimator(prefix=f"▶️ Running file {file_name} ({index}/{total_files}) ")
            animator.start()

            ignore_flags = " ".join(f"--ignore {path}" for path in skipped_files)
            command = (
                f"npx mocha --require mocha-suppress-logs --no-config "
                f"--extension ts {test_file} {ignore_flags} "
                f"--reporter json --timeout 10000 --no-warnings"
            )

            node_env_options = {
                "NODE_OPTIONS": "--loader ts-node/esm --no-warnings=ExperimentalWarning --no-deprecation"
            }

            try:
                stdout = self.command_service.run_command_silently(
                    command,
                    cwd=self.config.destination_folder,
                    env_vars=node_env_options,
                )
                repaired_json_string = repair_json(stdout)
                parsed = json.loads(repaired_json_string)

                if isinstance(parsed, dict):
                    all_parsed_tests.extend(parsed.get("tests", []))
                    all_parsed_failures.extend(parsed.get("failures", []))
                else:
                    self.logger.warning(
                        f"Mocha output for {test_file} was not a JSON object (got {type(parsed)}). "
                        f"Skipping test/failure extraction for this file."
                    )
                    self.logger.debug(f"Parsed content for {test_file}: {parsed}")

                animator.stop()
                sys.stdout.write(f"\r{' ' * 80}\r✅ {file_name} ({index}/{total_files})\n")
            except subprocess.TimeoutExpired:
                animator.stop()
                sys.stdout.write(f"\r{' ' * 80}\r🔍 {file_name} ({index}/{total_files}) - Timed out.\n")
            except json.JSONDecodeError:
                animator.stop()
                self.logger.error(f"Failed to parse JSON from Mocha for {test_file}.")
                self.logger.error(f"Original stdout:\n{stdout}")
                if repaired_json_string:
                    self.logger.error(f"After json_repair attempt:\n{repaired_json_string}")
                sys.stdout.write(
                    f"\r❌ {file_name} ({index}/{total_files}) - "
                    "Failed to parse test output. Check agent logs.\n"
                )
            except Exception as e:
                if not animator.is_stop_set():  # Check if the event is NOT set (i.e., running)
                    animator.stop()
                self.logger.error(f"Unexpected error during test run for {test_file}: {e}", exc_info=True)
                sys.stdout.write(
                    f"\r❌ {file_name} ({index}/{total_files}) - " f"Unexpected error. Check agent logs.\n"
                )

        return all_parsed_tests, all_parsed_failures

    def _report_tests(self, tests: List[Dict[str, str]], failures=None) -> Dict[str, int]:
        if failures is None:
            failures = []
        grouped_tests = defaultdict(list)

        seen = set()
        all_results = []

        for test in tests + failures:
            key = test.get("fullTitle", "") or test.get("title", "")
            if key and key not in seen:
                seen.add(key)
                all_results.append(test)

        passed_tests = sum(1 for test in all_results if not test.get("err"))
        total_tests = len(all_results)
        review_tests = total_tests - passed_tests

        for test in all_results:
            full_title = test.get("fullTitle", "")
            suite_title = full_title.replace(test.get("title", ""), "").strip() or "Ungrouped"
            grouped_tests[suite_title].append(test)

        for suite, tests in grouped_tests.items():
            self.logger.info(f"\n📂 {suite}")
            for test in tests:
                title = test["title"]
                duration = f"({test.get('duration')}ms)" if test.get("duration") else ""

                if test.get("err"):
                    self.logger.warning(f"    🔍 {title}")
                else:
                    self.logger.info(f"    ✅ {title} {duration}")

        self.logger.info("\n🎉 Test run completed")
        self.logger.info(f"\n✅ {passed_tests} tests passed")
        self.logger.info(f"🔍 {review_tests} tests flagged require further review\n")
        return {"total_tests": total_tests, "passed_tests": passed_tests, "review_tests": review_tests}

    def run_tests_flow(
        self, test_files: List[Dict[str, str]], interactive: bool = True
    ) -> Optional[TestRunMetrics]:
        test_data = self._get_runnable_files(test_files)
        runnable_files = test_data.runnable
        skipped_count = len(test_data.skipped)

        if not runnable_files:
            self.logger.warning("⚠️ No test files can be run due to compilation errors.")
            return TestRunMetrics(total_tests=0, passed_tests=0, review_tests=0, skipped_files=skipped_count)

        if not self._prompt_to_run_tests(interactive=interactive):
            self.logger.info("\n🔵 Test run skipped.")
            return None

        results, hook_failures = self._run_tests(runnable_files, test_data.skipped)
        report_metrics = self._report_tests(results, hook_failures)

        return TestRunMetrics(
            total_tests=report_metrics["total_tests"],
            passed_tests=report_metrics["passed_tests"],
            review_tests=report_metrics["review_tests"],
            skipped_files=skipped_count,
        )
