"""Utility to prevent test coverage regressions on pull requests."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        required=True,
        help="Path to the Coverage XML generated from the base branch.",
    )
    parser.add_argument(
        "--pr",
        required=True,
        help="Path to the Coverage XML generated from the pull request.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-4,
        help="Permitted floating point tolerance when comparing coverage values.",
    )
    return parser.parse_args()


def load_line_rate(path: str) -> float:
    """Load the overall line-rate from a Coverage XML file."""

    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:  # pragma: no cover - failure indicates malformed XML
        raise SystemExit(f"Failed to parse coverage report '{path}': {exc}") from exc

    root = tree.getroot()
    try:
        return float(root.attrib["line-rate"])
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"Coverage report '{path}' does not contain a valid 'line-rate' attribute.") from exc


def main() -> int:
    args = parse_args()

    base_rate = load_line_rate(args.base)
    pr_rate = load_line_rate(args.pr)

    if pr_rate + args.tolerance < base_rate:
        percent_delta = (pr_rate - base_rate) * 100
        message = (
            "Test coverage decreased: " f"base={base_rate:.2%}, PR={pr_rate:.2%}, delta={percent_delta:.2f}%"
        )
        print(message, file=sys.stderr)
        return 1

    print("Coverage check passed: " f"base={base_rate:.2%}, PR={pr_rate:.2%}.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
