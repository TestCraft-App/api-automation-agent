import json

import json
import os
import glob

POSTMAN_COLLECTION_PATH = os.path.join(os.path.dirname(__file__), "../../CatCafeDemo.postman_collection.json")


# Dynamically find the latest generated-framework_* folder
def get_latest_generated_tests_root():
    generated_base = os.path.join(os.path.dirname(__file__), "../../generated")
    candidates = glob.glob(os.path.join(generated_base, "generated-framework_*"))
    if not candidates:
        raise RuntimeError("No generated-framework_* folders found.")
    latest = max(candidates, key=os.path.getmtime)
    return os.path.join(latest, "src/tests/Adopt-a-cat/")


# Count all requests in the Postman collection
def count_postman_requests():
    def _count_items(items):
        count = 0
        for item in items:
            if "request" in item:
                count += 1
            if "item" in item:
                count += _count_items(item["item"])
        return count

    with open(POSTMAN_COLLECTION_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return _count_items(data["item"])

# Recursively count all generated .spec.ts files in the generated test output
GENERATED_TESTS_ROOT = os.path.join(
    os.path.dirname(__file__), "../../generated/generated-framework_20251201-231721/src/tests/Adopt-a-cat/"
)


def count_generated_spec_files():
    generated_tests_root = get_latest_generated_tests_root()
    return len([f for f in glob.glob(os.path.join(generated_tests_root, "**", "*.spec.ts"), recursive=True)])


def test_all_postman_requests_have_generated_files():
    postman_count = count_postman_requests()
    generated_count = count_generated_spec_files()
    assert (
        postman_count == generated_count
    ), f"Expected {postman_count} generated test files, found {generated_count}."
