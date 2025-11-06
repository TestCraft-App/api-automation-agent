# Evaluation Suite

This evaluation suite provides infrastructure for evaluating LLMService generation methods, with a focus on model-graded evaluations.

## Overview

The evaluation suite allows you to:
- Define test cases with API definitions and evaluation criteria
- Run `generate_first_test` and other generation methods
- Automatically grade generated files using LLM-based evaluation
- Generate detailed reports of evaluation results

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
    └── main_dataset/               # Example dataset folder
        ├── main_dataset.json       # Dataset file (must match folder name)
        ├── definitions/            # API definition files
        │   └── user_post_api.yaml
        └── models/                 # Model files (TypeScript)
            ├── requests/
            ├── responses/
            └── services/
```

## Usage

### 1. Prepare Test Data

1. Create a dataset folder (e.g., `evaluations/data/main_dataset/`)
2. Create a dataset JSON file named `{folder_name}.json` (e.g., `main_dataset.json`)
3. Place API definition files in the `definitions/` subfolder
4. Place model files (TypeScript) in the `models/` subfolder

### 2. Run Evaluation

```bash
python evaluations/evaluation_runner_main.py \
  --test-data-folder evaluations/data/main_dataset 
```

### Arguments

- `--test-data-folder`: Path to the dataset folder (required). The dataset JSON file should be named `{folder_name}.json` inside this folder.
- `--output-dir`: Directory to save evaluation results (default: `evaluations/reports`)

### 3. Review Results

Results are saved as JSON files in the output directory with timestamps. The console will also display a summary.

## Dataset Format

See `evaluations/data/README.md` for detailed information about the dataset format and structure.

## Example Dataset

See `evaluations/data/main_dataset/` for a complete example of a dataset folder structure.

## Model Grading

The evaluation uses LLM-based grading to assess whether generated files meet the specified criteria. The grader:
- Takes the generated file content and evaluation criteria
- Uses an LLM to evaluate compliance
- Returns a structured result with pass/fail, score, feedback, and reasoning

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

## Future Evaluations

The infrastructure is designed to support additional evaluation methods:
- `generate_models`
- `generate_additional_tests`
- `fix_typescript`

These can be added by extending the `EvaluationRunner` class.

