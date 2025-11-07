# Evaluation Test Data

This folder contains test data for evaluations. Each dataset should be organized in its own folder.

## Dataset Folder Structure

Each dataset must be organized in a dedicated folder with the following structure:

```
evaluations/data/
└── {dataset_name}/                    # Dataset folder (e.g., main_dataset)
    ├── {dataset_name}.json            # Dataset file (must match folder name)
    ├── definitions/                   # API definition files
    │   └── *.yaml or *.json
    └── models/                        # Model files (TypeScript)
        ├── requests/                  # Request models
        ├── responses/                 # Response models
        └── services/                  # Service models
```

See `evaluations/data/main_dataset/` for a complete example:

### Required Components

- **Dataset JSON File**: Must be named `{folder_name}.json` and placed directly in the dataset folder
- **API Definition Files**: Placed in the `definitions/` subfolder
- **Model Files**: TypeScript files placed in the `models/` subfolder (can be organized in subdirectories like `requests/`, `responses/`, `services/`)

## Dataset JSON File

A dataset file should be a JSON file with the following structure:

```json
{
  "dataset_name": "main_dataset",
  "test_cases": [
    {
      "test_id": "test_001",
      "name": "create_user_post_endpoint",
      "api_definition_file": "test_001_user_post_api.yaml",
      "model_files": [
        "requests/test_001_UserModel.ts",
        "services/test_001_UserService.ts"
      ],
      "evaluation_criteria": "The generated test should include proper setup/teardown hooks and test the main positive scenario"
    }
  ]
}
```

### Fields

- `dataset_name`: Name of the evaluation dataset (should match the folder name)
- `test_cases`: Array of test cases
  - `test_id`: **Required** unique identifier for the test case (e.g., "test_001"). This is used as a prefix for file names to enable easy linking when reviewing datasets.
  - `name`: Unique name for the test case
  - `api_definition_file`: Name of the API definition file (YAML/JSON) in the `definitions/` folder. **Must be prefixed with test_id** (e.g., "test_001_user_post_api.yaml").
  - `model_files`: **Required** list of model file paths relative to the `models/` folder. **The filename must be prefixed with test_id** (e.g., "requests/test_001_UserModel.ts"). The test_id prefix will be automatically removed from the filename and "src/models/" will be prepended when creating GeneratedModel objects for evaluation.
  - `evaluation_criteria`: Description of what the generated test should meet

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

See `evaluations/data/main_dataset/definitions/test_001_user_post_api.yaml` for a complete example of an API definition file for a POST `/users` endpoint.

## Model Files

Model files are TypeScript files that represent the models and services that `generate_first_test` receives as input. These files are placed in the `models/` subfolder and can be organized in subdirectories like `requests/`, `responses/`, and `services/`.

### File Format

Model files should be valid TypeScript files containing:
- **Request/Response Models**: TypeScript interfaces representing data models (e.g., `UserModel.ts`)
- **Service Models**: TypeScript classes extending `ServiceBase` with API endpoint methods (e.g., `UserService.ts`)

### Test ID Prefix

The **filename** (not the directory path) must be prefixed with the `test_id` from the dataset. For example:
- `requests/test_001_UserModel.ts`
- `services/test_001_UserService.ts`

### Examples

See `evaluations/data/main_dataset/models/` for examples of model files:
- `requests/test_001_UserModel.ts` - Example request/response model
- `services/test_001_UserService.ts` - Example service model


## Example Dataset

See `evaluations/data/main_dataset/main_dataset.json` for a complete example.

