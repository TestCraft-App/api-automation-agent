bash
git clone https://github.com/TestCraft-App/api-automation-agent.git
bash
bash
env
env
bash
graphql
generated-framework_[timestamp]/    # Or the Destination Folder selected
bash
bash
bash
bash
bash
bash
bash
bash
bash
env

# API Automation Agent

An open-source AI Agent that automatically generates an automation framework from your OpenAPI/Swagger specification or Postman collection, based on the [api-framework-ts-mocha template](https://github.com/damianpereira86/api-framework-ts-mocha).

---

## Multi-OpenAPI Specification Support

### Recent Fixes and Improvements

- **Supports loading and merging multiple OpenAPI specification files (YAML or JSON) in a single run.**
- **Robust error handling** for empty or invalid API spec files. The agent will skip empty files and log parsing errors without crashing.
- **Merging logic** updated to correctly combine API definitions using the `.definitions` attribute, matching the `APIDefinition` class structure.
- **CLI accepts multiple API spec file paths as arguments:**

```sh
python main.py apis/api1.yaml apis/api2.yaml apis/api3.yaml
```

The agent will load, validate, and merge all provided specs before generating the framework and models.

---

### Unified Swagger & OpenAPI 3.x Support

- **Added support for both Swagger 2.x (definitions) and OpenAPI 3.x (components/schemas) specifications.**
- Extended parsing logic in `APIDefinition.from_dict` to normalize both formats consistently.
- API paths and verbs are now represented using the `APIPath` and `APIVerb` classes, ensuring:
  - Consistent handling of HTTP methods
  - Normalized path representation (removes versioning/api prefixes)
  - Safe serialization of verb YAML content
- Fixed previous bug where `'dict' object has no attribute 'read'` occurred due to unsafe YAML parsing.
- The agent now generates models and tests seamlessly across mixed Swagger/OpenAPI inputs.

#### Example Usage

```sh
# Merge Swagger 2.x and OpenAPI 3.x specs in a single run
python main.py apis/swagger_petstore.yaml apis/openapi_users.yaml
```

The agent will automatically detect the format and generate a unified framework.

---

## Features

- Generates type-safe service and data models
- Generates test suites for every endpoint
- Reviews and fixes code issues and ensures code quality and best practices
- Includes code formatting and linting
- Runs tests with detailed reporting and assertions
- Migrates Postman collections to an open source automation framework, maintaining test structure and run order

---

## Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- OpenAI API key or Anthropic API key (**Anthropic API key required by default**)

---

## Installation

1. **Clone the repository:**
	```sh
	git clone https://github.com/TestCraft-App/api-automation-agent.git
	cd api-automation-agent
	```
2. **Install Python dependencies:**
	```sh
	pip install -r requirements.txt
	```
3. **Set up environment variables:**
	```sh
	cp example.env .env
	```
4. **Edit the `.env` file with your API keys:**
	```env
	OPENAI_API_KEY=your_openai_api_key_here
	ANTHROPIC_API_KEY=your_anthropic_api_key_here
	```

---

## Large Language Models

This project supports both Anthropic and OpenAI language models:

### Default Model

> **Claude 4 Sonnet** (`claude-sonnet-4-20250514`) is the default and recommended model
>
> - Provides superior code generation and understanding
> - Offers the best balance of performance and cost
> - **Strongly recommended:** Other models may not provide satisfactory results for this specific use case

### Supported Models

**Anthropic**
- Claude 4 Sonnet (`claude-sonnet-4-20250514`)
- Claude 3.7 Sonnet (`claude-3-7-sonnet-latest`)
- Claude 3.5 Sonnet (`claude-3-5-sonnet-latest`)

**OpenAI**
- GPT-5 (`gpt-5`)
- GPT-4o (`gpt-4o`)
- GPT-4.1 (`gpt-4.1`)
- O3 (`o3`)
- O4 Mini (`o4-mini`)

You can configure your preferred model in the `.env` file:

```env
MODEL=o4-mini
```

> **Important:** Before using any model, please check the current pricing and costs on the respective provider's website (Anthropic or OpenAI). Model costs can vary significantly and may impact your usage budget.

---

## Usage

Run the agent using the following command:

```sh
python ./main.py <path_or_url_to_openapi_definition>
```

The agent accepts either:

- A local file path to your OpenAPI/Swagger specification or Postman collection
- A URL to a JSON or YAML OpenAPI/Swagger specification (**URL not supported for Postman collections**)

### Options

- `--destination-folder`: Specify output directory (default: `./generated-framework_[timestamp]`)
- `--use-existing-framework`: Use an existing framework instead of creating a new one
- `--endpoints`: Generate framework for specific endpoints (can specify multiple)
- `--generate`: Specify what to generate (default: `models_and_tests`)
  - `models`: Generate only the data models
  - `models_and_first_test`: Generate data models and the first test for each endpoint
  - `models_and_tests`: Generate data models and complete test suites
- `--list-endpoints`: List the endpoints that can be used with the `--endpoints` flag

> **Note:** The `--endpoints`, `--generate`, `--list-endpoints`, and `--use-existing-framework` options are only available when using Swagger/OpenAPI specifications. When using Postman collections, only the `--destination-folder` parameter is fully supported.

#### Examples

```sh
# Generate framework from a local file
python ./main.py api-spec.yaml

# Generate framework from a URL
python ./main.py https://api.example.com/swagger.json

# Generate list root endpoints
python ./main.py api-spec.yaml --list-endpoints

# Generate complete framework with all endpoints
python ./main.py api-spec.yaml

# Generate models and tests for specific endpoints using an existing framework
python ./main.py api-spec.yaml --use-existing-framework --destination-folder ./my-api-framework --endpoints /user /store

# Generate only data and service models for all endpoints
python ./main.py api-spec.yaml --generate models

# Generate models and first test for each endpoint in a custom folder
python ./main.py api-spec.yaml --generate models_and_first_test --destination-folder ./quick-tests

# Combine options to generate specific endpoints with first test only
python ./main.py api-spec.yaml --endpoints /store --generate models_and_first_test
```

The generated framework will follow the structure:

```text
generated-framework_[timestamp]/    # Or the Destination Folder selected
├── src/
│   ├── base/                       # Framework base classes
│   ├── models/                     # Generated TypeScript interfaces and API service classes
│   └── tests/                      # Generated test suites
├── package.json
├── ...
└── tsconfig.json
```

---

## Postman Collection Migration

The API Automation Agent can now convert your Postman collections into TypeScript automated test frameworks, preserving the structure and test logic of your collections.

### Supported Features

- Converts Postman Collection v2.0 format JSON files into a TypeScript test framework
- Maintains the original folder structure of your Postman collection
- Preserves test run order for consistent test execution
- Creates service files by grouping API routes by path
- Migrates test scripts and assertions

### Limitations

- Only supports local Postman collection files (**no HTTP download support yet**)
- Currently only supports Postman Collection v2.0 format
- Scripts contained in folders (rather than requests) are not processed
- Limited CLI support - only the `--destination-folder` parameter is fully supported with Postman collections

### Best Practices

The migration works best with well-structured APIs where:

- Endpoints are organized logically by resource
- Similar endpoints (e.g., `/users`, `/users/{id}`) are grouped together
- HTTP methods follow REST conventions

#### Usage

```sh
# Migrate a Postman collection to TypeScript test framework
python ./main.py path/to/postman_collection.json --destination-folder ./my-api-tests
```

---

## Testing the Agent

To try out the agent without using your own API specification, you can use one of the following test APIs:

- **CatCafe API**: Test API created by [@CodingRainbowCat](https://github.com/CodingRainbowCat) specifically for testing the agent.
- **Pet Store API**: Public test API

#### Examples

**Cat Cafe**

```sh
# /adopters endpoints
python ./main.py http://localhost:3000/swagger.json --endpoints /adopters
```

**Pet Store**

```sh
# /store endpoints
python ./main.py https://petstore.swagger.io/v2/swagger.json --endpoints /store
```

These are simple and small examples that include basic CRUD operations and are ideal for testing the agent's capabilities.

> **Estimated cost (with claude-sonnet-4-20250514) to run each example above: US$ ~0.3**

You can combine endpoints to test larger scenarios:

```sh
python ./main.py http://localhost:3000/swagger.json --endpoints /adopters /pet
```

Or simply run it for the whole API:

```sh
python ./main.py http://localhost:3000/swagger.json
```

---

## Running Tests

### Test Structure

- Unit tests are located in `tests/unit/`
- Integration tests are in `tests/integration/`
- Test fixtures and mocks are in `tests/fixtures/`

### Running the Test Suite

1. **Install test dependencies:**
	```sh
	pip install -r requirements.txt
	pip install -r requirements-test.txt  # Additional test dependencies
	```
2. **Run all tests:**
	```sh
	pytest
	```
3. **Run specific test categories:**
	```sh
	pytest tests/unit/          # Run only unit tests
	pytest tests/integration/   # Run only integration tests
	```
4. **Run tests with coverage report:**
	```sh
	pytest --cov=src --cov-report=term --cov-config=.coveragerc
	```

### Test Best Practices

- All external LLM calls are mocked to keep tests fast and free of API costs
- Use the `@pytest.mark.asyncio` decorator for async tests
- Follow the naming convention: `test_<function_name>_<scenario>`
- Keep tests focused and isolated
- Use fixtures for common setup and teardown

---

## Performance Benchmarking

This project includes a benchmark tool designed to evaluate the performance of different Large Language Models (LLMs) in generating API test frameworks using this agent. It automates running the agent against an OpenAPI specification for various LLMs and collects quantifiable metrics.

For detailed instructions on how to set up, run, and interpret the benchmark results, please refer to the [Benchmark README](./benchmarks/README.md).

---

## Checkpoints

The checkpoints feature allows you to save and restore the state of the framework generation process. This is useful if you need to interrupt the process and resume it later without losing progress.

### Purpose

The purpose of the checkpoints feature is to provide a way to save the current state of the framework generation process and restore it later.

### How to Use

1. **Saving State:** The state is automatically saved at various points during the framework generation process.
2. **Restoring State:** If a previous run was interrupted, you will be prompted to resume the process when you run the agent again.
3. **Clearing Checkpoints:** After successful completion, the checkpoints are automatically cleared.

### Implementation

Implemented in `src/utils/checkpoint.py` using the `shelve` module to persist state.

---

## Contribution Guidelines

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request to the original repo
8. Check the project board for tasks.

---

## Code Formatting

- **Black** is used for Python formatting (line length 88, Python 3.7+)
- Configured for auto-format in VS Code
- Run manually with:
  ```sh
  black .
  ```

---

## Logging

Dual logging strategy:

1. **Console Output:** INFO-level user-friendly logs
2. **File Logging:** DEBUG-level detailed logs in `logs/[framework-name].log`

Control with `.env`:

```env
DEBUG=False
LANGCHAIN_DEBUG=False
```

---

## License

Licensed under the MIT License - see `LICENSE`.

---

## Acknowledgments

- OpenAI and Anthropic for their AI models
- All contributors who have helped build and improve this project
