"""Main entry point for running evaluations."""

import argparse
import json
import os
import sys
from datetime import datetime

# Add project root to Python path BEFORE importing from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from dotenv import load_dotenv  # noqa: E402

from src.adapters.config_adapter import DevConfigAdapter  # noqa: E402
from src.adapters.processors_adapter import ProcessorsAdapter  # noqa: E402
from src.configuration.config import Config  # noqa: E402
from src.container import Container  # noqa: E402
from src.services.file_service import FileService  # noqa: E402
from src.services.llm_service import LLMService  # noqa: E402
from src.utils.logger import Logger  # noqa: E402

from evaluations.models.evaluation_dataset import EvaluationDataset  # noqa: E402
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


def save_evaluation_results(results, output_dir: str, dataset_name: str) -> str:
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


def print_evaluation_summary(results):
    """Print a summary of evaluation results to console."""
    print("\n" + "-" * 120)
    print("DETAILED RESULTS")
    print("-" * 120)

    for result in results.results:
        status_symbol = {
            "GRADED": "✓",
            "NOT_EVALUATED": "!",
            "ERROR": "✗",
        }.get(result.status, "?")
        print(f"\n{status_symbol} [{result.test_id}] {result.test_case_name} [{result.status}]")
        print(f"  API Definition: {result.api_definition_file}")
        if result.error_message:
            print(f"  Error: {result.error_message}")
        if result.generated_files:
            print(f"  Generated Files: {', '.join(result.generated_files)}")
        if result.grade_result:
            if result.grade_result.score is not None:
                print(f"  Score: {result.grade_result.score:.2f}")
            if result.grade_result.evaluation:
                print("  Evaluation:")
                for item in result.grade_result.evaluation:
                    marker = "PASS" if item.met else "FAIL"
                    print(f"    - [{marker}] {item.criteria}: {item.details}")
            if result.grade_result.reasoning:
                print(f"  Score Reasoning: {result.grade_result.reasoning}")

    print("\n" + "=" * 120)
    print("EVALUATION SUMMARY")
    print("=" * 120)
    print(f"Dataset: {results.dataset_name}")
    print(f"Total Test Cases: {results.total_test_cases}")
    print(f"Graded: {results.graded_count}")
    print(f"Not Evaluated: {results.not_evaluated_count}")
    print(f"Errors: {results.error_count}")
    print(f"Input Tokens: {results.total_input_tokens}")
    print(f"Output Tokens: {results.total_output_tokens}")
    print(f"Total Cost (USD): ${results.total_cost:.4f}")
    avg_text = f"{results.average_score:.2f}" if results.average_score is not None else "N/A"
    print(f"Average Score: {avg_text}")
    if results.generated_files_path:
        print(f"Generated Files: {results.generated_files_path}")

    print("=" * 120)


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

    os.makedirs(args.output_dir, exist_ok=True)

    from evaluations.models.evaluation_dataset import EvaluationSummary, EvaluationRunResult

    all_results: list[EvaluationRunResult] = []

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

        print(f"\nLoading evaluation dataset from: {dataset_file}")
        dataset = load_evaluation_dataset(dataset_file)

        print("Initializing services...")
        config_adapter = DevConfigAdapter()
        processors_adapter = ProcessorsAdapter(config=config_adapter.config)
        container = Container(config_adapter=config_adapter, processors_adapter=processors_adapter)
        container.init_resources()

        config: Config = container.config()
        Logger.configure_logger(config)

        file_service = FileService()
        llm_service = LLMService(config, file_service)

        evaluation_runner = EvaluationRunner(
            config=config,
            llm_service=llm_service,
            file_service=file_service,
            test_data_folder=dataset_folder,
        )

        results = evaluation_runner.run_evaluation(dataset)

        print(f"\nSaving results to: {args.output_dir}")
        results_path = save_evaluation_results(results, args.output_dir, dataset.dataset_name)
        print(f"Results saved to: {results_path}")

        print_evaluation_summary(results)
        all_results.append(results)

    if len(all_results) > 1:
        total_test_cases = sum(r.total_test_cases for r in all_results)
        total_graded = sum(r.graded_count for r in all_results)
        total_not_evaluated = sum(r.not_evaluated_count for r in all_results)
        total_errors = sum(r.error_count for r in all_results)
        total_input_tokens = sum(r.total_input_tokens for r in all_results)
        total_output_tokens = sum(r.total_output_tokens for r in all_results)
        total_cost = sum(r.total_cost for r in all_results)

        score_values = [r.average_score for r in all_results if r.average_score is not None]
        average_score_across_datasets = sum(score_values) / len(score_values) if score_values else None

        summary = EvaluationSummary(
            total_datasets=len(all_results),
            total_test_cases=total_test_cases,
            total_graded=total_graded,
            total_not_evaluated=total_not_evaluated,
            total_errors=total_errors,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_cost=total_cost,
            average_score_across_datasets=average_score_across_datasets,
            dataset_results=all_results,
        )

        print("\n" + "=" * 120)
        print("AGGREGATED SUMMARY")
        print("=" * 120)
        print(f"Datasets evaluated: {summary.total_datasets}")
        print(f"Total Test Cases: {summary.total_test_cases}")
        print(f"Total Graded: {summary.total_graded}")
        print(f"Total Not Evaluated: {summary.total_not_evaluated}")
        print(f"Total Errors: {summary.total_errors}")
        print(f"Total Input Tokens: {summary.total_input_tokens}")
        print(f"Total Output Tokens: {summary.total_output_tokens}")
        print(f"Total Cost (USD): ${summary.total_cost:.4f}")
        if summary.average_score_across_datasets is not None:
            print(f"Average Score Across Datasets: {summary.average_score_across_datasets:.2f}")
        else:
            print("Average Score Across Datasets: N/A")
        print("=" * 120)


if __name__ == "__main__":
    main()
