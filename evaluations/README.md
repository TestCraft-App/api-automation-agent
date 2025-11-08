# Evaluation Suite

This evaluation suite provides infrastructure for evaluating LLMService generation methods, with a focus on model-graded evaluations.

## Overview

The evaluation suite allows you to:
- Define test cases with API definitions and evaluation criteria
- Run evaluations for `generate_first_test` and `generate_models`
- Automatically grade generated files using LLM-based evaluation
- Generate detailed reports of evaluation results

> **Important**: The API does not need to exist because the generated tests are not executed. Evaluation is based solely on the generated code quality, allowing you to easily create extensive datasets with specific scenarios without requiring a running API server.

## Structure

```
evaluations/
├── __init__.py
├── README.md
├── evaluation_runner_main.py      # Main entry point
├── models/
│   ├── __init__.py
│   └── evaluation_dataset.py      # Pydantic models for datasets and results
├── services/
│   ├── __init__.py
│   ├── model_grader.py            # LLM-based grading service
│   └── evaluation_runner.py       # Main evaluation orchestration
└── data/
    ├── generate_first_test_dataset/               # Example first-test dataset
    └── generate_models_dataset/                   # Example models dataset
```

## Usage

### Setup Requirements

Before running evaluations:

1. Copy `.env.example` (or follow the project README) to create a `.env` file.
2. Add API keys for the LLM vendor you plan to use (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).

Refer back to the main README for exact environment variable names and additional instructions.

### 1. Prepare Test Data

1. Create a dataset folder (e.g., `evaluations/data/generate_first_test_dataset/`)
2. Create a dataset JSON file named `{folder_name}.json` (e.g., `generate_first_test_dataset.json`)
3. Place API definition files in the `definitions/` subfolder
4. Place model files (TypeScript) in the `models/` subfolder (leave empty if not needed, e.g., for `generate_models`)

See `README.md` inside data folder for more details on test data requirements. 

### 2. Run Evaluation

```bash
python evaluations/evaluation_runner_main.py \
  --test-data-folder evaluations/data/generate_first_test_dataset 
```

You can evaluate multiple datasets in a single run by repeating the flag:

```bash
python evaluations/evaluation_runner_main.py \
  --test-data-folder evaluations/data/generate_first_test_dataset \
  --test-data-folder evaluations/data/generate_models_dataset
```

### Arguments

- `--test-data-folder`: Path to the dataset folder (required). The dataset JSON file should be named `{folder_name}.json` inside this folder.
- `--output-dir`: Directory to save evaluation results (default: `evaluations/reports`)
- `--llm`: Optional override for the LLM model to use (e.g., `--llm GPT_5`)

### 3. Review Results

Results are saved as JSON files in the output directory with timestamps. The console will also display a summary.

Summary metrics include:
- Total test cases and pass/fail/error counts
- LLM model used for the evaluation
- Token usage (input, output, total) and total evaluation cost (USD)
- Average score across all graded test cases (0.0 – 1.0)
- Status values per test case:
  - `GRADED` – the file was generated and evaluated
  - `NOT_EVALUATED` – no file was generated or grading was unavailable
  - `ERROR` – an exception occurred while processing the test case

Generated files are stored for inspection under `evaluations/reports/generated-files/{dataset_name}/{test_id}/`.
Each run appends a timestamp to `{dataset_name}`, e.g. `my_dataset_20251107_153045/test_001`.

## Dataset Format

See `evaluations/data/README.md` for detailed information about the dataset format and structure.

## Example Datasets

- `evaluations/data/generate_first_test_dataset/` – sample dataset for `generate_first_test`
- `evaluations/data/generate_models_dataset/` – sample dataset for `generate_models`

## Model Grading

The evaluation uses LLM-based grading to assess whether generated files meet the specified criteria. The grader:
- Takes the generated file content and evaluation criteria
- Uses an LLM to evaluate compliance
- Returns a structured result with score, detailed criterion-by-criterion evaluation, and reasoning

The grading model uses the same configuration as the generation model (from your `.env` file).

## Current Evaluations

### `generate_first_test`

This evaluation:
1. Loads the API definition from the `definitions/` folder within the dataset folder
2. Loads model files (TypeScript) from the `models/` folder within the dataset folder and converts them to `GeneratedModel` objects
3. Runs `generate_first_test` with the API definition and loaded models
4. Reads the generated test file content
5. Grades it against the evaluation criteria using model grading
6. Returns a structured result

### `generate_models`

This evaluation:
1. Loads the API definition from the `definitions/` folder within the dataset folder
2. Runs `generate_models` to produce TypeScript model files
3. Reads the generated models files content
4. Grades the generated models against the evaluation criteria using model grading
5. Returns a structured result

## Future Evaluations

The infrastructure is designed to support additional evaluation methods (e.g., `generate_additional_tests`, `fix_typescript`). These can be added by extending the `EvaluationRunner` class.

