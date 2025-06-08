import argparse
import json
import os
import re
import yaml
from typing import Dict, List

GROUND_TRUTHS_DIR = os.path.join(os.path.dirname(__file__), "ground_truths")


def load_ground_truth(path: str) -> Dict:
    with open(path, "r") as f:
        if path.endswith((".yml", ".yaml")):
            return yaml.safe_load(f)
        return json.load(f)


def list_available_ground_truths(directory: str = GROUND_TRUTHS_DIR) -> List[Dict]:
    ground_truths = []
    if not os.path.isdir(directory):
        return ground_truths
    for file in os.listdir(directory):
        if file.endswith((".yml", ".yaml", ".json")):
            data = load_ground_truth(os.path.join(directory, file))
            ground_truths.append(
                {"file": file, "spec": data.get("spec"), "endpoints": list(data.get("endpoints", {}).keys())}
            )
    return ground_truths


def sanitize_endpoint(endpoint: str) -> str:
    return endpoint.strip("/").replace("/", "_").replace("{", "").replace("}", "")


def parse_test_file(path: str) -> List[str]:
    with open(path, "r") as f:
        content = f.read()
    suite_match = re.search(r"describe\(\s*[\"']([^\"']+)[\"']", content)
    suite = suite_match.group(1) if suite_match else "Unknown Suite"
    tests = re.findall(r"it\(\s*[\"']([^\"']+)[\"']", content)
    return [f"{suite}::{t}" for t in tests]


def collect_tests(framework_path: str, endpoint: str, verb: str) -> List[str]:
    tests_path = os.path.join(framework_path, "src", "tests", sanitize_endpoint(endpoint))
    pattern = f"{verb.upper()}-*.spec.ts"
    collected: List[str] = []
    if not os.path.isdir(tests_path):
        return collected
    for file in os.listdir(tests_path):
        if re.fullmatch(pattern.replace("*", ".*"), file):
            collected.extend(parse_test_file(os.path.join(tests_path, file)))
    return collected


def calculate_coverage(ground_truth_tests: List[str], actual_tests: List[str]) -> Dict:
    gt_set = set(ground_truth_tests)
    actual_set = set(actual_tests)
    matched = gt_set & actual_set
    extra = actual_set - gt_set
    coverage = round(len(matched) / len(gt_set) * 100, 2) if gt_set else 0.0
    return {"coverage_percent": coverage, "extra_tests": sorted(extra), "matched_tests": sorted(matched)}


def run(args: argparse.Namespace):
    if args.command == "list":
        for item in list_available_ground_truths():
            print(f"{item['file']}: spec={item['spec']}, endpoints={', '.join(item['endpoints'])}")
        return

    data = load_ground_truth(args.ground_truth)
    endpoint_data = data.get("endpoints", {}).get(args.endpoint, {})
    gt_tests = endpoint_data.get(args.verb.lower(), [])
    actual_tests = collect_tests(args.framework_path, args.endpoint, args.verb)
    results = calculate_coverage(gt_tests, actual_tests)
    print(json.dumps(results, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test Coverage Benchmark")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List available ground truths")

    run_parser = sub.add_parser("run", help="Run coverage benchmark")
    run_parser.add_argument("--ground-truth", required=True, help="Path to ground truth YAML/JSON")
    run_parser.add_argument("--framework-path", required=True, help="Path to generated framework root")
    run_parser.add_argument("--endpoint", required=True, help="Endpoint to evaluate")
    run_parser.add_argument("--verb", required=True, help="HTTP verb to evaluate")

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    run(args)
