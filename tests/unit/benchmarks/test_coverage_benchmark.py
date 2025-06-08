import json
from pathlib import Path

from benchmarks.test_coverage.coverage_benchmark import (
    calculate_coverage,
    collect_tests,
    parse_test_file,
    sanitize_endpoint,
)


SAMPLE_TS = """
describe('User Suite', () => {
  it('should get user', () => {});
  it('extra test', () => {});
});
"""


def test_parse_test_file(tmp_path):
    f = tmp_path / "GET-sample.spec.ts"
    f.write_text(SAMPLE_TS)
    tests = parse_test_file(str(f))
    assert tests == [
        "User Suite::should get user",
        "User Suite::extra test",
    ]


def test_collect_and_calculate(tmp_path):
    framework = tmp_path / "fw"
    test_dir = framework / "src" / "tests" / sanitize_endpoint("/user")
    test_dir.mkdir(parents=True)
    (test_dir / "GET-sample.spec.ts").write_text(SAMPLE_TS)

    gt_tests = ["User Suite::should get user"]
    actual = collect_tests(str(framework), "/user", "get")
    result = calculate_coverage(gt_tests, actual)

    assert result["coverage_percent"] == 100.0
    assert "User Suite::extra test" in result["extra_tests"]
