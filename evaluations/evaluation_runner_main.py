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
    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Dataset: {results.dataset_name}")
    print(f"Total Test Cases: {results.total_test_cases}")
    print(f"Passed: {results.passed_count}")
    print(f"Failed: {results.failed_count}")
    print(f"Errors: {results.error_count}")
    print("\n" + "-" * 80)
    print("DETAILED RESULTS")
    print("-" * 80)

    for result in results.results:
        status_symbol = "✓" if result.status == "SUCCESS" else "✗"
        print(f"\n{status_symbol} [{result.test_id}] {result.test_case_name} [{result.status}]")
        print(f"  API Definition: {result.api_definition_file}")
        if result.error_message:
            print(f"  Error: {result.error_message}")
        if result.generated_files:
            print(f"  Generated Files: {', '.join(result.generated_files)}")
        if result.grade_result:
            print(f"  Grade: {'PASSED' if result.grade_result.passed else 'FAILED'}")
            if result.grade_result.score is not None:
                print(f"  Score: {result.grade_result.score:.2f}")
            print(f"  Feedback: {result.grade_result.feedback}")
            if result.grade_result.reasoning:
                print(f"  Reasoning: {result.grade_result.reasoning}")

    print("\n" + "=" * 80)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run evaluations on LLMService generation methods")

    parser.add_argument(
        "--test-data-folder",
        type=str,
        required=True,
        help=(
            "Path to the dataset folder (e.g., evaluations/data/main_dataset). "
            "The dataset JSON file should be named {folder_name}.json"
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

    if not os.path.exists(args.test_data_folder):
        print(f"Error: Test data folder not found: {args.test_data_folder}")
        sys.exit(1)

    folder_name = os.path.basename(os.path.normpath(args.test_data_folder))
    dataset_file = os.path.join(args.test_data_folder, f"{folder_name}.json")

    if not os.path.exists(dataset_file):
        print(f"Error: Dataset file not found: {dataset_file}")
        print(f"Expected dataset file: {folder_name}.json in {args.test_data_folder}")
        sys.exit(1)

    print(f"Loading evaluation dataset from: {dataset_file}")
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
        test_data_folder=args.test_data_folder,
    )

    print(f"\nRunning evaluation for dataset: {dataset.dataset_name}")
    results = evaluation_runner.run_evaluation(dataset)

    print(f"\nSaving results to: {args.output_dir}")
    results_path = save_evaluation_results(results, args.output_dir, dataset.dataset_name)
    print(f"Results saved to: {results_path}")

    print_evaluation_summary(results)


if __name__ == "__main__":
    main()
