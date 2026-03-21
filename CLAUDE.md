# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Agent that generates TypeScript test frameworks (Mocha-based) from OpenAPI/Swagger specs or Postman collections. Uses LangChain for multi-provider LLM support (Anthropic, OpenAI, Google, AWS Bedrock). The generated frameworks follow the [api-framework-ts-mocha](https://github.com/damianpereira86/api-framework-ts-mocha) template.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Run all tests with coverage
pytest --cov=src --cov-report=term --cov-config=.coveragerc

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run a specific test file
pytest tests/unit/services/test_file_service.py

# Run tests matching a pattern
pytest -k "test_file_service"

# Format code (line length: 110, target: py310)
black .

# Lint (max-line-length: 110, ignores E203)
flake8 .

# Run the agent
python ./main.py <path_or_url_to_openapi_or_postman>

# Run benchmarks
python benchmarks/benchmark_runner.py --openapi-spec <spec> --llms GPT_5_1,CLAUDE_SONNET_4_5 --endpoints /users --output-dir ./benchmark_results

# Run all evaluations
python evaluations/evaluation_runner_main.py --all --llms CLAUDE_SONNET_4_5 --grader CLAUDE_SONNET_4_5 --output-dir ./eval_results

# Run a single evaluation dataset
python evaluations/evaluation_runner_main.py --test-data-folder evaluations/data/prompt_injection_dataset --llms CLAUDE_SONNET_4_5 --grader CLAUDE_SONNET_4_5
```

## Architecture

### Dependency Injection

`src/container.py` defines a `dependency-injector` DeclarativeContainer that wires all services. `main.py` initializes the container with config and processor adapters, then calls `container.wire()`. All services are injected — never instantiate them directly.

### Core Flow

1. **Parse API spec** — `SwaggerProcessor` (OpenAPI) or `PostmanProcessor` (Postman) produces an `APIDefinition` model
2. **Generate code via LLM** — `LLMService` sends prompts (from `prompts/*.txt`) through LangChain, returns `FileSpec` objects
3. **Orchestrate** — `FrameworkGenerator` coordinates the pipeline: models → first test → additional tests → TypeScript fix loop
4. **Execute tests** — `TestController` runs `npm test` (Mocha) in the generated framework and collects results

### Key Patterns

- **Processor pattern**: `APIProcessor` selects `SwaggerProcessor` or `PostmanProcessor` based on `DataSource` enum. Swagger uses strategy pattern for schema filters (`BaseSchemaFilter` → `OpenAPIV2SchemaFilter`/`OpenAPIV3SchemaFilter`).
- **State management**: `FrameworkStateManager` persists generation progress to `framework-state.json` for incremental generation. `Checkpoint` (using `shelve`) handles crash recovery via a decorator pattern.
- **Configuration**: `Config` dataclass in `src/configuration/config.py`. Models defined as enum in `src/configuration/models.py` with pricing info. Dev/Prod adapters in `src/adapters/config_adapter.py`.
- **LLM tools**: `src/ai_tools/` defines tools the LLM can invoke (file creation/reading) as LangChain tool definitions.
- **Prompt files**: All LLM system prompts live as `.txt` files in `prompts/`.

### Testing Strategy

- **Unit tests** (`tests/unit/`): All LLM calls are mocked. Use `pytest-mock`. Naming: `test_<function>_<scenario>`.
- **Integration tests** (`tests/integration/`): Marked with `@pytest.mark.integration`.
- **Evaluations** (`evaluations/`): 14 datasets, 114 test cases. Five eval types: assertion-based, rule-based, model-graded, hybrid, security. Use `--all` to run all datasets.
- **Benchmarks** (`benchmarks/`): Performance/cost metrics across LLM models.

CI enforces coverage non-regression on PRs via `scripts/coverage_guard.py`.

## Post-Change Checklist

After modifying code in `src/`:
1. Run relevant tests — don't skip, fix failures before considering the task complete
2. Review and update docs if needed: `README.md`, `USAGE-GUIDE.txt`, `benchmarks/README.md`
