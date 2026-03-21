# Evaluation Suite

This evaluation suite provides infrastructure for evaluating LLMService generation methods using a taxonomy of evaluation types: assertion-based, rule-based, model-graded, hybrid, and security.

## Overview

The evaluation suite allows you to:
- Define test cases with API definitions and evaluation criteria
- Run evaluations across 10 case types and 5 grading methods
- Grade generated code using deterministic rules, LLM-based evaluation, or both
- Generate detailed reports with criteria-level aggregation

> **Important**: The API does not need to exist because the generated tests are not executed. Evaluation is based solely on the generated code quality, allowing you to easily create extensive datasets with specific scenarios without requiring a running API server.

## Eval Taxonomy

| Type | Description | Deterministic? | LLM Grading Cost | Example |
|------|-------------|----------------|-------------------|---------|
| **Assertion-Based** | Set/list comparison | Yes | Zero | `get_additional_models` |
| **Rule-Based** | Regex/string pattern checks on generated code | Yes | Zero | `architectural_compliance`, `prompt_injection` |
| **Model-Graded** | LLM evaluates semantic quality | No | $ | `generate_first_test`, `generate_models` |
| **Hybrid** | Rule-based structural + model-graded semantic, combined score | Partially | $ | `hallucination_detection`, `prompt_adherence` |
| **Security** | Adversarial evals with rule-based checks | Yes | Zero | `prompt_injection` |

## Structure

```
evaluations/
├── __init__.py
├── README.md
├── evaluation_runner_main.py      # Main entry point
├── dashboard.html                 # Interactive HTML results dashboard
├── models/
│   ├── __init__.py
│   └── evaluation_dataset.py      # Pydantic models for datasets and results
├── services/
│   ├── __init__.py
│   ├── evaluation_runner.py       # Main evaluation orchestration
│   ├── evaluation_data_loader.py  # Test data loading utilities
│   ├── evaluation_file_writer.py  # Generated file persistence
│   ├── model_grader.py            # LLM-based grading service (temperature=0)
│   ├── mock_file_reading_tool.py  # Mock tool for get_additional_models tests
│   └── evaluators/                # Strategy pattern evaluators
│       ├── __init__.py
│       ├── base_evaluator.py                    # Abstract base + rule-based engine
│       ├── first_test_evaluator.py              # generate_first_test (OpenAPI & Postman)
│       ├── models_evaluator.py                  # generate_models (OpenAPI & Postman)
│       ├── additional_tests_evaluator.py        # generate_additional_tests
│       ├── additional_models_evaluator.py       # get_additional_models (assertion-based)
│       ├── prompt_injection_evaluator.py        # prompt_injection (rule-based/security)
│       ├── hallucination_evaluator.py           # hallucination_detection (hybrid)
│       ├── architectural_compliance_evaluator.py # architectural_compliance (rule-based)
│       ├── prompt_adherence_evaluator.py        # prompt_adherence (hybrid)
│       └── fix_typescript_evaluator.py          # fix_typescript (hybrid)
└── data/
    ├── generate_first_test_dataset/         # 16 cases, model-graded, Users domain
    ├── generate_first_test_postman_dataset/  # 16 cases, model-graded, Users domain
    ├── generate_additional_tests_dataset/    # 6 cases, model-graded, Users domain
    ├── generate_models_dataset/              # 7 cases, model-graded, Users domain
    ├── get_additional_models_dataset/        # 3 cases, assertion-based, Multi domain
    ├── prompt_injection_dataset/             # 9 cases, rule-based/security, Multi domain
    ├── hallucination_detection_dataset/      # 8 cases, hybrid, Multi domain (new)
    ├── ecommerce_first_test_dataset/         # 10 cases, model-graded, E-commerce domain
    ├── healthcare_first_test_dataset/        # 6 cases, model-graded, Healthcare domain
    ├── complex_schema_first_test_dataset/    # 6 cases, model-graded, Multi domain
    ├── ecommerce_models_dataset/             # 7 cases, model-graded, E-commerce domain
    ├── architectural_compliance_dataset/     # 8 cases, rule-based, Users domain
    ├── prompt_adherence_dataset/             # 6 cases, hybrid, Users domain
    └── fix_typescript_dataset/               # 6 cases, hybrid, Users domain
```

**Total: 14 datasets, 114 test cases.**

## Architecture

The evaluation system uses a **Strategy Pattern** for extensibility:

- **`EvaluationRunner`**: Orchestrates evaluation runs, manages parallel execution, and aggregates results
- **`BaseEvaluator`**: Abstract base class providing shared logic (config management, file grading, Postman preprocessing, rule-based criteria engine)
- **Concrete Evaluators**: Each handles specific case types

### Rule-Based Criteria Engine

The `BaseEvaluator._evaluate_rule_based_criteria()` method supports these check types:

| Check Type | Description |
|------------|-------------|
| `contains` | String must be present in generated code |
| `not_contains` | String must NOT be present |
| `regex_match` | Regex pattern must match |
| `regex_not_match` | Regex pattern must NOT match |
| `file_exists` | A generated file path must contain the pattern |
| `import_check` | An import statement for the pattern must exist |

### Deterministic Scoring

The model grader computes scores deterministically as `criteria_met / total_criteria` rather than using the LLM's freeform score. The LLM evaluates each criterion as met/not-met (what it's good at), but the final score is a simple calculation. Grading uses `temperature=0` for reproducibility.

### Adding a New Evaluator

1. Create a new class extending `BaseEvaluator` in `evaluations/services/evaluators/`
2. Define `supported_case_types` (list of case type strings it handles)
3. Implement the `evaluate()` method
4. Add the class to `_create_evaluators()` in `evaluation_runner.py`

## Usage

### Setup Requirements

Before running evaluations:

1. Copy `.env.example` (or follow the project README) to create a `.env` file.
2. Add API keys for the LLM vendor you plan to use (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`).

### Run Evaluation

```bash
# All datasets
python evaluations/evaluation_runner_main.py \
  --all --llms CLAUDE_SONNET_4_6 --grader CLAUDE_SONNET_4_6

# Single dataset
python evaluations/evaluation_runner_main.py \
  --test-data-folder evaluations/data/generate_first_test_dataset

# Multiple datasets
python evaluations/evaluation_runner_main.py \
  --test-data-folder evaluations/data/generate_first_test_dataset \
  --test-data-folder evaluations/data/prompt_injection_dataset

# Specific test cases only
python evaluations/evaluation_runner_main.py \
  --test-data-folder evaluations/data/generate_first_test_dataset \
  --test-ids test_001

# Smoke test: run test_001 from every dataset
python evaluations/evaluation_runner_main.py \
  --all --test-ids test_001 --llms CLAUDE_SONNET_4_6

# Multiple LLMs with specific grader
python evaluations/evaluation_runner_main.py \
  --test-data-folder evaluations/data/generate_first_test_dataset \
  --llms GPT_5_1,CLAUDE_SONNET_4_6 \
  --grader CLAUDE_SONNET_4_6
```

### Arguments

- `--all`: Run all datasets found in `evaluations/data/`
- `--test-data-folder`: Path to a dataset folder (repeatable, can combine with `--all`)
- `--output-dir`: Directory to save evaluation results (default: `evaluations/reports`)
- `--llms`: Comma-separated list of LLM models to evaluate
- `--grader`: LLM model to use for grading (independent of tested models)
- `--test-ids`: Filter to run specific test cases by test ID

### Review Results

The console output includes:
- **Summary table** with dataset, LLM, test cases, graded count, tokens, cost, average score (includes a TOTAL row when running multiple datasets)
- **Eval method distribution** showing counts and average scores by evaluation method
- **Most failed criteria** listing the criteria with lowest pass rates
- **Artifact locations** for JSON results and generated files

#### Interactive Results Dashboard

**Live dashboard**: [testcraft-app.github.io/api-automation-agent/evaluations/dashboard.html](https://testcraft-app.github.io/api-automation-agent/evaluations/dashboard.html)

The Dashboard is also available locally at `evaluations/dashboard.html`. It auto-loads published runs from the repo, or you can use the folder picker to load local results. Features:

- **Leaderboard** — pivot table comparing models across all datasets, with color-coded scores and cost
- **Drill-down** — click any leaderboard cell to filter the detail table to that model+dataset
- **Detail table** — filter and sort individual test results by dataset, model, eval method, status, or score
- **Expandable rows** — per-criterion details, reasoning, and generated files
- **Run selector** — switch between evaluation runs via a modal with run metadata

## Evaluators

### Model-Graded Evaluators

- **`FirstTestEvaluator`** (`generate_first_test`, `generate_first_test_postman`): Generates a test from an API spec and models, grades with LLM
- **`ModelsEvaluator`** (`generate_models`): Generates TypeScript models from an API spec, grades with LLM
- **`AdditionalTestsEvaluator`** (`generate_additional_tests`): Generates additional tests from a seed test, grades with LLM

### Assertion-Based Evaluators

- **`AdditionalModelsEvaluator`** (`get_additional_models`): Compares returned file paths against expected files

### Rule-Based Evaluators

- **`PromptInjectionEvaluator`** (`prompt_injection`): Generates code then checks for injection patterns using string/regex rules
- **`ArchitecturalComplianceEvaluator`** (`architectural_compliance`): Generates code then checks framework patterns, import conventions, TypeScript quality

### Hybrid Evaluators

- **`HallucinationEvaluator`** (`hallucination_detection`): Rule-based checks for structural hallucinations + model-graded checks for semantic ones
- **`PromptAdherenceEvaluator`** (`prompt_adherence`): Rule-based structural checks + model-graded semantic assessment
- **`FixTypescriptEvaluator`** (`fix_typescript`): Fixes broken TypeScript files, then rule-based checks that errors are gone + model-graded that logic is preserved

## Dataset Format

### Standard Fields

```json
{
  "dataset_name": "my_dataset",
  "test_cases": [
    {
      "case_type": "generate_first_test",
      "test_id": "test_001",
      "name": "descriptive_name",
      "api_definition_file": "test_001_api.yaml",
      "model_files": ["services/test_001_Service.ts"],
      "evaluation_criteria": ["LLM-graded criterion 1", "LLM-graded criterion 2"]
    }
  ]
}
```

### Rule-Based Criteria (for rule-based, hybrid, and security evaluations)

```json
{
  "rule_based_criteria": [
    {
      "check_type": "not_contains",
      "pattern": "alert(",
      "description": "Must not contain alert() calls"
    },
    {
      "check_type": "regex_match",
      "pattern": "\\.should\\.",
      "description": "Must use Chai should-style assertions"
    }
  ]
}
```

### Fix TypeScript Fields

```json
{
  "case_type": "fix_typescript",
  "broken_files": ["test_001_broken.ts"],
  "compiler_errors": ["error TS2344: Type mismatch..."]
}
```

## Datasets

| Dataset | Cases | Eval Type | Domain |
|---------|-------|-----------|--------|
| generate_first_test | 16 | Model-graded | Users |
| generate_first_test_postman | 16 | Model-graded | Users |
| generate_additional_tests | 6 | Model-graded | Users |
| generate_models | 7 | Model-graded | Users |
| get_additional_models | 3 | Assertion-based | Multi |
| prompt_injection | 9 | Rule-based (security) | Multi |
| hallucination_detection | 8 | Hybrid | Multi |
| ecommerce_first_test | 10 | Model-graded | E-commerce |
| healthcare_first_test | 6 | Model-graded | Healthcare |
| complex_schema_first_test | 6 | Model-graded | Multi |
| ecommerce_models | 7 | Model-graded | E-commerce |
| architectural_compliance | 8 | Rule-based | Users |
| prompt_adherence | 6 | Hybrid | Users |
| fix_typescript | 6 | Hybrid | Users |
| **Total** | **114** | | |

## Security Evaluations

### Prompt Injection Dataset

The `prompt_injection_dataset` evaluates the agent's resistance to prompt injection attacks embedded in API specifications. Now uses **rule-based grading** (zero LLM grading cost) with 9 test cases covering:

- Alert injection via description fields
- HTTP exfiltration via external URLs
- Environment variable exfiltration
- Schema description injection (child_process)
- Social engineering via fake auth setup (filesystem reads)
- Example value injection (process.exit)
- OperationId injection
- Server URL manipulation
- Role confusion / system prompt override

### Hallucination Detection Dataset

Tests whether the LLM invents things not in the API spec:

- Fabricating fields not in the schema
- Creating request bodies for GET endpoints
- Calling non-existent service methods
- Using undefined enum values
- Adding authentication when spec has none
- Including readOnly fields in requests
- Asserting undocumented status codes

## Model Grading

The grader uses `temperature=0` for deterministic evaluation. Scores are computed as `criteria_met / total_criteria` regardless of the LLM's freeform score field.

### Configuring the Grader Model

The grader model can be configured via (in order of precedence):
1. `--grader CLAUDE_SONNET_4_6` (CLI argument)
2. `GRADER_MODEL=claude-sonnet-4-5` (environment variable)
3. `MODEL` from `.env` (fallback)
