# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

AI Agent that generates TypeScript test frameworks (Mocha-based) from OpenAPI/Swagger specs or Postman collections. Uses LangChain for multi-provider LLM support (Anthropic, OpenAI, Google, AWS Bedrock). The generated frameworks follow the [api-framework-ts-mocha](https://github.com/damianpereira86/api-framework-ts-mocha) template.

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

Keep verification proportional to the files and behavior changed:

1. Run the smallest relevant test file or test selection first, and fix failures before expanding the test scope.
2. When Python files change, invoke Black separately for each Python file touched by the current task; multi-file Black runs can stall during worker shutdown on Windows. Then run Flake8 once on that same changed-file set with `--jobs 1`. Do not include unrelated modified files from the shared worktree.
3. Run broader unit, integration, or coverage suites when the change crosses components or has wider behavioral risk. Changes in `src/` should receive relevant unit coverage at minimum.
4. Run formatting, linting, and tests as separate commands so a slow or failed step is easy to identify. Skip Python formatting and linting when no Python files changed.
5. Use repository-wide Black and Flake8 checks only for an explicit full validation or maintenance task. Generated frameworks, dependency trees, evaluation output, and benchmark reports are excluded by tool configuration. In the Windows Codex environment, partition a full Black check into one-file invocations to avoid the worker-shutdown stall.
6. Review documentation impact, especially `README.md`, `USAGE-GUIDE.txt`, `evaluations/README.md`, and `benchmarks/README.md`, and update only the documents affected by the change.
7. Inspect the final diff for accidental edits, generated artifacts, and changes belonging to other worktree users before handing off.

Reusable setup and command examples belong in `README.md`; this file defines how to choose and scope those checks.
