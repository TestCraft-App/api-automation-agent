import argparse
import concurrent.futures
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from tabulate import tabulate

# Add project root to Python path to allow importing project modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from dotenv import load_dotenv  # noqa: E402
from src.configuration.models import Model  # noqa: E402
from src.utils.logger import Logger as SrcLogger  # noqa: E402
from src.configuration.config import Config, GenerationOptions  # noqa: E402
from src.container import Container  # noqa: E402
from src.adapters.config_adapter import DevConfigAdapter  # noqa: E402
from src.adapters.processors_adapter import ProcessorsAdapter  # noqa: E402
from src.configuration.data_sources import get_processor_for_data_source  # noqa: E402
from src.processors.api_processor import APIProcessor  # noqa: E402
from src.framework_generator import FrameworkGenerator  # noqa: E402
from src.test_controller import TestController, TestRunMetrics  # noqa: E402
from src.models.usage_data import AggregatedUsageMetadata  # noqa: E402
from src.utils.checkpoint import toggle_checkpoints  # noqa: E402


class BenchmarkTestMetrics(BaseModel):
    generated_test_files_count: int = 0
    skipped_compilation_files_count: int = 0
    runnable_test_files_count: int = 0
    total_tests_executed: int = 0
    passed_tests: int = 0
    review_tests: int = 0


class BenchmarkResult(BaseModel):
    llm_model_value: str
    api_definition: str
    endpoints: List[str] = Field(default_factory=list)
    status: str = "PENDING"
    error_message: Optional[str] = None
    metrics: Optional[BenchmarkTestMetrics] = None
    duration_seconds: Optional[float] = None
    llm_usage_metadata: Optional[AggregatedUsageMetadata] = None
    generated_framework_path: Optional[str] = None


def _setup_benchmark_logger(level=logging.INFO):
    """Sets up a basic logger for the benchmark script itself."""
    logger = logging.getLogger("benchmark_runner")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_llm_choices() -> List[str]:
    """Returns a list of available LLM model names."""
    return [model.name for model in Model]


def parse_llms(llm_string: str) -> List[Model]:
    """Parses a comma-separated string of LLM names into a list of Model enums."""
    llm_names = [name.strip() for name in llm_string.split(",")]
    valid_llms = []
    available_models = get_llm_choices()
    for name in llm_names:
        try:
            valid_llms.append(Model[name])
        except KeyError:
            raise argparse.ArgumentTypeError(
                f"Invalid LLM model: {name}. Choices are: {', '.join(available_models)}"
            )
    if not valid_llms:
        raise argparse.ArgumentTypeError("At least one LLM model must be specified.")
    return valid_llms


def _run_benchmark_for_llm(
    llm_model_enum: Model, openapi_spec: str, endpoints: Optional[List[str]]
) -> BenchmarkResult:
    """Runs the benchmark for a single LLM model."""
    benchmark_logger = _setup_benchmark_logger()

    start_time = time.monotonic()
    llm_model_value = llm_model_enum.value

    result = BenchmarkResult(
        llm_model_value=llm_model_value,
        api_definition=openapi_spec,
        endpoints=endpoints if endpoints else [],
    )

    try:
        config_adapter = DevConfigAdapter()  # Uses .env for keys
        processors_adapter = ProcessorsAdapter(config=config_adapter.config)
        container = Container(config_adapter=config_adapter, processors_adapter=processors_adapter)
        container.init_resources()

        config: Config = container.config()

        dest_folder = f"{config.destination_folder}_benchmark_{llm_model_value}"
        config.update(
            {
                "api_definition": openapi_spec,
                "destination_folder": dest_folder,
                "endpoints": endpoints if endpoints else None,
                "generate": GenerationOptions.MODELS_AND_TESTS,
                "model": llm_model_enum,
                "use_existing_framework": False,
                "list_endpoints": False,
                "debug": False,
            }
        )

        SrcLogger.configure_logger(config)
        toggle_checkpoints(True)

        agent_setup_logger = SrcLogger.get_logger(__name__ + ".agent_setup")
        data_source = APIProcessor.set_data_source(openapi_spec, agent_setup_logger)
        config.update({"data_source": data_source})

        benchmark_logger.info(
            f"Agent Config: Dest='{config.destination_folder}', Model='{config.model.value}', "
            f"Src='{config.data_source}', Debug={config.debug}"
        )

        api_processor_instance = get_processor_for_data_source(data_source, container)
        container.api_processor.override(api_processor_instance)

        framework_generator: FrameworkGenerator = container.framework_generator()
        test_controller: TestController = container.test_controller()

        api_definitions = framework_generator.process_api_definition()
        framework_generator.setup_framework(api_definitions)
        framework_generator.create_env_file(api_definitions)
        framework_generator.generate(api_definitions, config.generate)
        test_files_details = framework_generator.run_final_checks(config.generate)

        result.llm_usage_metadata = framework_generator.get_aggregated_usage_metadata()

        generated_files_count = len(test_files_details) if test_files_details else 0

        if not test_files_details:
            benchmark_logger.warning(
                "No test files were generated or passed final checks. Skipping test run."
            )
            result.metrics = BenchmarkTestMetrics(
                generated_test_files_count=generated_files_count,
                skipped_compilation_files_count=generated_files_count,  # All generated files were skipped
                runnable_test_files_count=0,
                total_tests_executed=0,
                passed_tests=0,
                review_tests=0,
            )
        else:
            benchmark_logger.info(f"Proceeding to run tests for {generated_files_count} generated file(s)...")
            metrics_result: Optional[TestRunMetrics] = test_controller.run_tests_flow(
                test_files_details, interactive=False
            )
            if metrics_result:
                result.metrics = BenchmarkTestMetrics(
                    generated_test_files_count=generated_files_count,
                    skipped_compilation_files_count=metrics_result.skipped_files,
                    runnable_test_files_count=generated_files_count - metrics_result.skipped_files,
                    total_tests_executed=metrics_result.total_tests,
                    passed_tests=metrics_result.passed_tests,
                    review_tests=metrics_result.review_tests,
                )
            else:
                benchmark_logger.warning(
                    "Test run did not return metrics (e.g. skipped). Assuming 0 for all execution metrics."
                )
                result.metrics = BenchmarkTestMetrics(
                    generated_test_files_count=generated_files_count,
                    skipped_compilation_files_count=generated_files_count,
                    runnable_test_files_count=0,
                    total_tests_executed=0,
                    passed_tests=0,
                    review_tests=0,
                )

        result.status = "COMPLETED"
        result.generated_framework_path = dest_folder

    except Exception as e:
        benchmark_logger.error(f"Error during benchmark for LLM {llm_model_value}: {e}", exc_info=True)
        result.status = "FAILED"
        result.error_message = str(e)
    finally:
        end_time = time.monotonic()
        duration = end_time - start_time
        result.duration_seconds = round(duration, 2)

    return result


def _format_duration_for_display(duration_seconds: Optional[float]) -> str:
    """Formats duration in seconds to a human-readable string 'Xh Ym Zs', 'Ym Zs' or 'Ys'."""
    if isinstance(duration_seconds, (int, float)):
        hours = int(duration_seconds // 3600)
        remaining_seconds = duration_seconds % 3600
        minutes = int(remaining_seconds // 60)
        seconds = int(remaining_seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    return "N/A"


def _generate_json_report(
    benchmark_results: List[BenchmarkResult],
    output_dir: str,
    report_timestamp: str,
    benchmark_logger: logging.Logger,
):
    """Generates and saves the JSON benchmark report."""
    json_report_path = os.path.join(output_dir, f"benchmark_report_{report_timestamp}.json")
    results_for_json = [result.model_dump(mode="json") for result in benchmark_results]
    try:
        with open(json_report_path, "w") as f:
            json.dump(results_for_json, f, indent=4)
        benchmark_logger.info(f"Detailed benchmark report saved to: {json_report_path}\n")
        return json_report_path
    except IOError as e:
        benchmark_logger.error(f"Failed to write JSON report to {json_report_path}: {e}")
        return None


def _generate_csv_report(
    benchmark_results: List[BenchmarkResult],
    output_dir: str,
    report_timestamp: str,
    benchmark_logger: logging.Logger,
):
    """Generates and saves the CSV benchmark summary report."""
    csv_report_path = os.path.join(output_dir, f"benchmark_summary_{report_timestamp}.csv")
    headers = [
        "LLM Model",
        "Test Files",
        "Skipped Files",
        "Run Files",
        "Tests Run",
        "Passed",
        "Review",
        "Duration",
        "Input Tokens",
        "Output Tokens",
        "Fix Attempts",
        "Total Cost ($)",
    ]
    table_data = []
    for result in benchmark_results:
        metrics = result.metrics
        llm_usage = result.llm_usage_metadata
        formatted_duration = _format_duration_for_display(result.duration_seconds)
        formatted_cost = f"{llm_usage.total_cost:.4f}" if llm_usage else "N/A"

        row = [
            result.llm_model_value,
            metrics.generated_test_files_count if metrics else "N/A",
            metrics.skipped_compilation_files_count if metrics else "N/A",
            metrics.runnable_test_files_count if metrics else "N/A",
            metrics.total_tests_executed if metrics else "N/A",
            metrics.passed_tests if metrics else "N/A",
            metrics.review_tests if metrics else "N/A",
            formatted_duration,
            llm_usage.total_input_tokens if llm_usage else "N/A",
            llm_usage.total_output_tokens if llm_usage else "N/A",
            llm_usage.total_fix_attempts if llm_usage else "N/A",
            formatted_cost,
        ]
        table_data.append(row)

    try:
        with open(csv_report_path, "w", newline="") as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow(headers)
            writer.writerows(table_data)
        benchmark_logger.info(f"Benchmark summary table saved to: {csv_report_path}\n")
    except IOError as e:
        benchmark_logger.error(f"Failed to write CSV report to {csv_report_path}: {e}")


def _print_tabulate_report(
    benchmark_results: List[BenchmarkResult],
    openapi_spec_path: str,
    endpoints: Optional[List[str]],
    json_report_path: Optional[str],
    benchmark_logger: logging.Logger,
):
    """Prints the benchmark summary table to the console."""
    print("--- Benchmark Summary Table ---\n")
    print(f"OpenAPI Spec: {openapi_spec_path}")
    print(f"Endpoints   : {', '.join(endpoints) if endpoints else 'All'}", "\n")

    headers = [
        "LLM Model",
        "Test Files",
        "Skipped Files",
        "Run Files",
        "Tests Run",
        "Passed",
        "Review",
        "Duration",
        "Input Tokens",
        "Output Tokens",
        "Fix Attempts",
        "Total Cost ($)",
    ]
    table_data = []
    for result in benchmark_results:
        metrics = result.metrics
        llm_usage = result.llm_usage_metadata
        formatted_duration = _format_duration_for_display(result.duration_seconds)
        formatted_cost = f"{llm_usage.total_cost:.4f}" if llm_usage else "N/A"

        row = [
            result.llm_model_value,
            metrics.generated_test_files_count if metrics else "N/A",
            metrics.skipped_compilation_files_count if metrics else "N/A",
            metrics.runnable_test_files_count if metrics else "N/A",
            metrics.total_tests_executed if metrics else "N/A",
            metrics.passed_tests if metrics else "N/A",
            metrics.review_tests if metrics else "N/A",
            formatted_duration,
            llm_usage.total_input_tokens if llm_usage else "N/A",
            llm_usage.total_output_tokens if llm_usage else "N/A",
            llm_usage.total_fix_attempts if llm_usage else "N/A",
            formatted_cost,
        ]
        table_data.append(row)

    if table_data:
        table_string = tabulate(table_data, headers=headers, tablefmt="rounded_grid")
        for line in table_string.splitlines():
            print(line)
        if json_report_path:
            normalized_path = os.path.normpath(json_report_path)
            print(f"\nFor detailed benchmark metadata, see the JSON report at: {normalized_path}")
    else:
        benchmark_logger.info("No benchmark data to display in table.")


def _generate_reports(
    benchmark_results: List[BenchmarkResult],
    benchmark_logger: logging.Logger,
    args: argparse.Namespace,
):
    """Generates and saves/prints benchmark reports."""
    report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_report_path = _generate_json_report(
        benchmark_results, args.output_dir, report_timestamp, benchmark_logger
    )

    _generate_csv_report(benchmark_results, args.output_dir, report_timestamp, benchmark_logger)

    _print_tabulate_report(
        benchmark_results, args.openapi_spec, args.endpoints, json_report_path, benchmark_logger
    )


def run_benchmark(args: argparse.Namespace, benchmark_logger: logging.Logger) -> List[BenchmarkResult]:
    """Main function to run the benchmark."""
    load_dotenv(override=True)

    benchmark_logger.info("Starting API Generation Agent Benchmark")

    benchmark_results: List[BenchmarkResult] = []

    if args.load_results:
        benchmark_logger.info(f"Attempting to load results from: {args.load_results}")
        try:
            with open(args.load_results, "r") as f:
                loaded_data = json.load(f)
            benchmark_results = [BenchmarkResult(**result) for result in loaded_data]
            benchmark_logger.info(
                f"Successfully loaded {len(benchmark_results)} result(s) from {args.load_results}"
            )
        except FileNotFoundError:
            benchmark_logger.error(f"Error: Results file not found at {args.load_results}. Exiting.")
            sys.exit(1)
        except json.JSONDecodeError:
            benchmark_logger.error(
                f"Error: Could not decode JSON from {args.load_results}. "
                f"Ensure it is a valid JSON report. Exiting."
            )
            sys.exit(1)
        except Exception as e:
            benchmark_logger.error(
                f"Error: Could not parse benchmark results from {args.load_results}. " f"Error: {e}. Exiting."
            )
            sys.exit(1)
    else:
        benchmark_logger.info(f"OpenAPI Spec: {args.openapi_spec}")
        benchmark_logger.info(f"Endpoints: {', '.join(args.endpoints) if args.endpoints else 'All'}")
        benchmark_logger.info(f"LLMs to benchmark: {[llm.value for llm in args.llms]}")

        with concurrent.futures.ProcessPoolExecutor() as executor:
            future_to_llm = {
                executor.submit(
                    _run_benchmark_for_llm, llm_model, args.openapi_spec, args.endpoints
                ): llm_model
                for llm_model in args.llms
            }

            for llm_model_enum in args.llms:
                benchmark_logger.info(f"--- Submitting benchmark for LLM: {llm_model_enum.value} ---")

            for future in concurrent.futures.as_completed(future_to_llm):
                llm_model_enum = future_to_llm[future]
                try:
                    result_data = future.result()
                    benchmark_results.append(result_data)
                    benchmark_logger.info(
                        f"--- Completed benchmark for LLM: {llm_model_enum.value} "
                        f"(Status: {result_data.status}) ---"
                    )
                except Exception as exc:
                    benchmark_logger.error(
                        f"--- LLM {llm_model_enum.value} benchmark generated an exception: {exc} ---",
                        exc_info=True,
                    )
                    failed_result = BenchmarkResult(
                        llm_model_value=llm_model_enum.value,
                        api_definition=args.openapi_spec,
                        endpoints=args.endpoints if args.endpoints else [],
                        status="FAILED",
                        error_message=str(exc),
                    )
                    benchmark_results.append(failed_result)

    return benchmark_results


def _parse_args() -> argparse.Namespace:
    """Parses CLI arguments."""
    parser = argparse.ArgumentParser(description="API Generation Agent Benchmark CLI")

    parser.add_argument(
        "--openapi-spec",
        type=str,
        required=True,
        help="Path to the OpenAPI specification file (JSON or YAML).",
    )
    parser.add_argument(
        "--endpoints",
        type=str,
        nargs="+",
        help="Optional: Specific endpoint(s) to target. If not provided, all endpoints will be targeted.",
    )
    parser.add_argument(
        "--llms",
        type=parse_llms,
        required=True,
        help=f"Comma-separated list of LLM models to benchmark. " f"Choices: {', '.join(get_llm_choices())}.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmarks/reports",
        help="Directory to save benchmark reports (default: benchmarks/reports).",
    )
    parser.add_argument(
        "--load-results",
        type=str,
        default=None,
        help="Optional: Path to a previously generated JSON report file to load results from. "
        "If provided, the benchmark generation and execution steps are skipped.",
    )
    return parser.parse_args()


def main():
    start_time = time.monotonic()
    args = _parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    benchmark_logger = _setup_benchmark_logger()

    benchmark_results = run_benchmark(args, benchmark_logger)

    if not benchmark_results:
        benchmark_logger.warning("No benchmark results generated or loaded. Skipping report generation.")
    else:
        benchmark_logger.info("Generating benchmark reports...")
        _generate_reports(benchmark_results, benchmark_logger, args)

    end_time = time.monotonic()
    total_duration_seconds = end_time - start_time
    formatted_total_duration = _format_duration_for_display(total_duration_seconds)

    print(f"\n🏁 Benchmark finished in {formatted_total_duration} 🏁")


if __name__ == "__main__":
    main()
