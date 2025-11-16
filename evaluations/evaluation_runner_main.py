"""Main entry point for running evaluations."""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Optional, Tuple

from tabulate import tabulate

# Add project root to Python path BEFORE importing from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from dotenv import load_dotenv  # noqa: E402

from src.adapters.config_adapter import DevConfigAdapter  # noqa: E402
from src.adapters.processors_adapter import ProcessorsAdapter  # noqa: E402
from src.configuration.config import Config  # noqa: E402
from src.configuration.models import Model  # noqa: E402
from src.container import Container  # noqa: E402
from src.services.file_service import FileService  # noqa: E402
from src.services.llm_service import LLMService  # noqa: E402
from src.utils.logger import Logger  # noqa: E402

from evaluations.models.evaluation_dataset import (  # noqa: E402
    EvaluationDataset,
    EvaluationRunResult,
)
from evaluations.services.evaluation_runner import EvaluationRunner  # noqa: E402


def load_evaluation_dataset(dataset_path: str) -> EvaluationDataset:
    """
    Load an evaluation dataset from a JSON file.

    Args:
        dataset_path: Path to the JSON file containing the dataset

    Returns:
        EvaluationDataset loaded from the file
    """
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return EvaluationDataset.model_validate(data)
    except Exception as e:
        print(f"Error loading evaluation dataset from {dataset_path}: {e}")
        raise


def save_evaluation_results(results: EvaluationRunResult, output_dir: str, dataset_name: str) -> str:
    """
    Save evaluation results to a JSON file.

    Args:
        results: EvaluationRunResult to save
        output_dir: Directory to save results in
        dataset_name: Name of the dataset

    Returns:
        Path to the saved results file
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"evaluation_results_{dataset_name}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results.model_dump(mode="json"), f, indent=2)

    return filepath


def _get_llm_choices() -> List[str]:
    """Returns a list of available LLM model names."""
    return [model.name for model in Model]


def _parse_llms(llm_string: str) -> List[Model]:
    """
    Parse a comma-separated string of LLM names into a list of Model enums.

    Example:
        --llms GPT_5_1,CLAUDE_SONNET_4_5
    """
    llm_names = [name.strip() for name in llm_string.split(",") if name.strip()]
    valid_llms: List[Model] = []
    available_models = _get_llm_choices()

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


def _print_tabulated_summary(
    run_results: List[Tuple[EvaluationRunResult, str]],
) -> None:
    """
    Print a tabulated summary across all dataset/LLM evaluation runs.

    Columns:
      Dataset, LLM Model, Test Cases, Graded, Output Tokens, Total Cost ($), Average Score
    """
    if not run_results:
        print("No evaluation results to summarize.")
        return

    headers = [
        "Dataset",
        "LLM Model",
        "Test Cases",
        "Graded",
        "Output Tokens",
        "Total Cost ($)",
        "Average Score",
    ]

    table_data: List[list] = []
    for results, _ in run_results:
        avg_score_text = f"{results.average_score:.2f}" if results.average_score is not None else "N/A"
        cost_text = f"{results.total_cost:.4f}"

        table_data.append(
            [
                results.dataset_name,
                results.llm_model,
                results.total_test_cases,
                results.graded_count,
                results.total_output_tokens,
                cost_text,
                avg_score_text,
            ]
        )

    print("--- Evaluation Summary Table ---\n")
    table_string = tabulate(table_data, headers=headers, tablefmt="rounded_grid")
    for line in table_string.splitlines():
        print(line)


def _print_result_paths(run_results: List[Tuple[EvaluationRunResult, str]]) -> None:
    """
    After the summary table, print the JSON report and generated files locations
    for each dataset/LLM evaluation run.
    """
    if not run_results:
        return

    print("\nEvaluation artifacts:")
    for results, json_path in run_results:
        normalized_json = os.path.normpath(json_path)
        generated_path = (
            os.path.normpath(results.generated_files_path) if results.generated_files_path else "N/A"
        )
        print(
            f"- Dataset: {results.dataset_name} | LLM: {results.llm_model}\n"
            f"    JSON results    : {normalized_json}\n"
            f"    Generated files : {generated_path}"
        )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run evaluations on LLMService generation methods")

    parser.add_argument(
        "--test-data-folder",
        type=str,
        action="append",
        required=True,
        help=(
            "Path to a dataset folder (e.g., evaluations/data/generate_first_test_dataset). "
            "Provide this flag multiple times for multiple datasets, or supply a comma-separated list. "
            "Each dataset must contain a JSON file named {folder_name}.json."
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluations/reports",
        help="Directory to save evaluation results (default: evaluations/reports)",
    )

    parser.add_argument(
        "--llms",
        type=_parse_llms,
        help=(
            "Optional: Comma-separated list of LLM models to evaluate. "
            f"Choices: {', '.join(_get_llm_choices())}. "
            "Example: --llms GPT_5_1,CLAUDE_SONNET_4_5"
        ),
    )

    parser.add_argument(
        "--test-ids",
        type=str,
        action="append",
        help=(
            "Optional: Filter test cases by test ID. "
            "Provide this flag multiple times for multiple test IDs, or supply a comma-separated list. "
            "Example: --test-ids test_001 --test-ids test_002 or --test-ids test_001,test_002. "
            "If not provided, all test cases will be run."
        ),
    )

    return parser.parse_args()


def main():
    """Main entry point for evaluation runner."""
    load_dotenv(override=True)

    args = parse_args()

    dataset_folders: list[str] = []
    for entry in args.test_data_folder:
        parts = [part.strip() for part in entry.split(",") if part.strip()]
        dataset_folders.extend(parts)

    if not dataset_folders:
        print("Error: No dataset folders provided.")
        sys.exit(1)

    test_ids_filter: Optional[list[str]] = None
    if args.test_ids:
        test_ids_filter = []
        for entry in args.test_ids:
            parts = [part.strip() for part in entry.split(",") if part.strip()]
            test_ids_filter.extend(parts)
        print(f"Filtering to test IDs: {', '.join(test_ids_filter)}")

    os.makedirs(args.output_dir, exist_ok=True)

    llm_overrides: Optional[List[Model]] = args.llms if getattr(args, "llms", None) else None

    run_results: List[Tuple[EvaluationRunResult, str]] = []

    for dataset_folder in dataset_folders:
        dataset_folder = os.path.normpath(dataset_folder)

        if not os.path.exists(dataset_folder):
            print(f"Error: Test data folder not found: {dataset_folder}")
            sys.exit(1)

        folder_name = os.path.basename(dataset_folder)
        dataset_file = os.path.join(dataset_folder, f"{folder_name}.json")

        if not os.path.exists(dataset_file):
            print(f"Error: Dataset file not found: {dataset_file}")
            print(f"Expected dataset file: {folder_name}.json in {dataset_folder}")
            sys.exit(1)

        print(f"Loading evaluation dataset from: {dataset_file}\n")
        dataset = load_evaluation_dataset(dataset_file)

        models_to_run: List[Optional[Model]] = llm_overrides or [None]

        for override_model in models_to_run:
            print("Initializing services...")
            config_adapter = DevConfigAdapter()
            processors_adapter = ProcessorsAdapter(config=config_adapter.config)
            container = Container(config_adapter=config_adapter, processors_adapter=processors_adapter)
            container.init_resources()

            config: Config = container.config()
            if override_model is not None:
                config.update({"model": override_model})

            Logger.configure_logger(config)

            file_service = FileService()
            llm_service = LLMService(config, file_service)

            evaluation_runner = EvaluationRunner(
                config=config,
                llm_service=llm_service,
                file_service=file_service,
                test_data_folder=dataset_folder,
            )

            results = evaluation_runner.run_evaluation(dataset, test_ids_filter=test_ids_filter)

            print(f"\nSaving results to: {args.output_dir}")
            results_path = save_evaluation_results(results, args.output_dir, dataset.dataset_name)
            print(f"Results saved to: {results_path}\n")

            run_results.append((results, results_path))

    _print_tabulated_summary(run_results)
    _print_result_paths(run_results)


if __name__ == "__main__":
    main()
