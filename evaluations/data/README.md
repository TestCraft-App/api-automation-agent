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

### Required Components

- **Dataset JSON File**: Must be named `{folder_name}.json` and placed directly in the dataset folder
- **API Definition Files**: Placed in the `definitions/` subfolder
- **Model Files**: TypeScript files placed in the `models/` subfolder (can be organized in subdirectories like `requests/`, `responses/`, `services/`)

## Example Structure

See `evaluations/data/main_dataset/` for a complete example:

```
evaluations/data/main_dataset/
├── main_dataset.json                  # Dataset file
├── definitions/
│   └── user_post_api.yaml            # API definition
└── models/
    ├── requests/
    │   └── UserModel.ts              # Request model
    ├── responses/
    └── services/
        └── UserService.ts            # Service model
```

## Dataset Format

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

### Test ID Prefix Behavior

The `test_id` prefix serves the purpose of **File Organization**. The filename is prefixed with test_id in the dataset folder for easy identification and linking.

Example:
- Dataset path: `models/requests/test_001_UserModel.ts`
- After removing test_id from filename: `requests/UserModel.ts`
- Final GeneratedModel path: `src/models/requests/UserModel.ts`

During evaluation, the test_id prefix is removed from the filename and "src/models/" is prepended to create realistic paths.

## Example Dataset

See `evaluations/data/main_dataset/main_dataset.json` for a complete example.

