# Evaluation Test Data

This folder contains test data for evaluations. Each dataset should be organized in its own folder.

## Dataset Folder Structure

Each dataset must be organized in a dedicated folder with the following structure:

```
evaluations/data/
└── {dataset_name}/                    # Dataset folder (e.g., generate_first_test_dataset)
    ├── {dataset_name}.json            # Dataset file (must match folder name)
    ├── definitions/                   # API definition files
    │   └── *.yaml or *.json
    ├── models/                        # Model files (TypeScript)
    │   ├── requests/                  # Request models
    │   ├── responses/                 # Response models
    │   └── services/                  # Service models
    └── tests/                         # Seed test files (TypeScript, optional)
```

See `evaluations/data/generate_first_test_dataset/` for a complete example:

### Required Components

- **Dataset JSON File**: Must be named `{folder_name}.json` and placed directly in the dataset folder
- **API Definition Files**: Placed in the `definitions/` subfolder
- **Model Files**: TypeScript files placed in the `models/` subfolder (can be organized in subdirectories like `requests/`, `responses/`, `services/`)

## Dataset JSON File

A dataset file should be a JSON file with the following structure:

```json
{
  "dataset_name": "generate_first_test_dataset",
  "test_cases": [
    {
      "case_type": "generate_first_test",
      "test_id": "test_001",
      "name": "create_user_post_endpoint",
      "api_definition_file": "test_001_user_post_api.yaml",
      "model_files": [
        "requests/test_001_UserModel.ts",
        "services/test_001_UserService.ts"
      ],
      "evaluation_criteria": [
        "Include proper setup/teardown hooks",
        "Test the main positive scenario"
      ]
    }
  ]
}
```

### Fields

- `dataset_name`: Name of the evaluation dataset (should match the folder name)
- `test_cases`: Array of test cases
  - `case_type`: Type of evaluation to run. Supported values: `"generate_first_test"` (default), `"generate_models"`, `"generate_additional_tests"`.
  - `test_id`: **Required** unique identifier for the test case (e.g., "test_001"). This is used to organize generated artifacts and file prefixes.
  - `name`: Unique name for the test case
  - `api_definition_file`: Name of the API definition file (YAML/JSON) in the `definitions/` folder. **Must be prefixed with test_id** (e.g., "test_001_user_post_api.yaml").
  - `model_files`: List of model file paths relative to the `models/` folder. Filenames may optionally start with a `test_###_` prefix (e.g., "requests/test_001_UserModel.ts"); if present, the prefix is removed automatically and "src/models/" is prepended when creating GeneratedModel objects for evaluation. Leave empty if no seed model files are required (e.g., for `generate_models` evaluations).
  - `first_test_file`: Single test file path relative to the `tests/` folder. Used only for `"generate_additional_tests"` to provide the initial seed test. Filenames may optionally start with a `test_###_` prefix; if present, the prefix is removed and `"src/tests/"` is prepended.
  - `evaluation_criteria`: Ordered list of specific criteria the generated test should satisfy

## API Definition Files

API definition files are OpenAPI Specification (YAML or JSON) files that define a single API endpoint with one HTTP verb (GET, POST, PUT, DELETE, etc.). Each file should contain:

> **Note**: The API does not need to exist or be running. Since the evaluation only assesses the generated test code (tests are not executed), you can create API definitions for any scenario without requiring an actual API server.

- **Single Endpoint**: Only one path in the `paths` section
- **Single HTTP Verb**: Only one HTTP method (verb) for that path
- **Complete Schemas**: All referenced schemas must be included in the `components/schemas` section

### Test ID Prefix

The **filename** must be prefixed with the `test_id` from the dataset. For example:
- `test_001_user_post_api.yaml`

### Structure

The API definition file should match the output of the `process_api_definition` method in the `FrameworkGenerator` class.

### Example

See `evaluations/data/generate_first_test_dataset/definitions/user_post_api.yaml` for a complete example of an API definition file for a POST `/users` endpoint.

## Model Files

Model files are TypeScript files that represent the models and services that `generate_first_test` receives as input. These files are placed in the `models/` subfolder and can be organized in subdirectories like `requests/`, `responses/`, and `services/`.

### File Format

Model files should be valid TypeScript files containing:
- **Request/Response Models**: TypeScript interfaces representing data models (e.g., `UserModel.ts`)
- **Service Models**: TypeScript classes extending `ServiceBase` with API endpoint methods (e.g., `UserService.ts`)

### Test Prefix

If you choose to prefix filenames with the `test_id` (recommended when you want to distinguish different variations), the prefix will be stripped automatically. For example:
- `requests/test_001_UserModel.ts` → `src/models/requests/UserModel.ts`
- `services/test_001_UserService.ts` → `src/models/services/UserService.ts`

If no prefix is present, the filename is used as-is.

### Examples

See `evaluations/data/generate_first_test_dataset/models/` for examples of model files:
- `requests/UserModel.ts` - Example request/response model
- `services/test_001_UserService.ts` - Example service model

## Seed Test Files (for generate_additional_tests)

When running the `generate_additional_tests` evaluation, you must provide the initial test file(s) that the LLM will extend. Place these files under the `tests/` subfolder.

### File Format

- Files should be valid test files.
- Filenames can optionally include the `test_id` prefix. Examples:
  - `tests/test_001_initial_test.ts` → transformed to `src/tests/test_001_initial_test.ts`
  - `tests/smoke/initial_test.ts` → transformed to `src/tests/smoke/initial_test.ts`

### Requirements

- Provide exactly one existing test file via the `first_test_file` field for each `"generate_additional_tests"` case.
- The content should represent the "first test" that `generate_additional_tests` builds upon.


## Example Dataset

See `evaluations/data/generate_first_test_dataset/generate_first_test_dataset.json` for a complete example.

