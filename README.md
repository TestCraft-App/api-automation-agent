# API Automation Agent

An open-source AI Agent that automatically generates an automation framework from your OpenAPI/Swagger specification or Postman collection, based on the api-framework-ts-mocha template (https://github.com/damianpereira86/api-framework-ts-mocha).

## Features

- Generates type-safe service and data models
- Generates test suites for every endpoint
- Reviewes and fixes code issues and ensures code quality and best practices
- Includes code formatting and linting
- Runs tests with detailed reporting and assertions
- Migrates Postman collections to an open source automation framework, mantaining test structure and run order.

## Usage

### Standalone Installer

Download the standalone executable:

#### Prerequisites

- Windows 7+ or macOS 10.14+
- API key (OpenAI or Anthropic)
- Node.js 18+

#### Windows Users

1. Go to [Releases](https://github.com/TestCraft-App/api-automation-agent/releases)
2. Download `api-automation-agent-windows.zip`
3. Extract and follow the included `USAGE-GUIDE.txt`

#### Mac Users

1. Go to [Releases](https://github.com/TestCraft-App/api-automation-agent/releases)
2. Download `api-automation-agent-macos.tar.gz`
3. Extract and follow the included `USAGE-GUIDE.txt`
4. Make the executable runnable: `chmod +x api-automation-agent`

### Manual Installation (for development)

#### Prerequisites

- Node.js 18 or higher
- Python 3.8 or higher
- OpenAI API key or Anthropic API key (Anthropic API key required by default)

#### Installation Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/TestCraft-App/api-automation-agent.git
   cd api-automation-agent
   ```

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:

   ```bash
   cp example.env .env
   ```

4. Edit the `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Large Language Models

This project supports both Anthropic and OpenAI language models:

### Default Model

**Claude 4 Sonnet** (claude-sonnet-4-20250514) is the default and recommended model

- Provides superior code generation and understanding
- Offers the best balance of performance and cost
- **Strongly recommended**: Other models may not provide satisfactory results for this specific use case

### Supported Models

**Anthropic**

- Claude 4 Sonnet (claude-sonnet-4-20250514) - **Recommended**
- Claude 3.5 Sonnet (claude-3-5-sonnet-latest)
- Claude 3.7 Sonnet (claude-3-7-sonnet-latest)

**OpenAI**

- GPT-5 (gpt-5)
- GPT-4o (gpt-4o)
- GPT-4.1 (gpt-4.1)
- O3 (o3)
- O4 Mini (o4-mini)

You can configure your preferred model in the `.env` file:

```env
MODEL=o4-mini
```

> **Important**: Before using any model, please check the current pricing and costs on the respective provider's website (Anthropic or OpenAI). Model costs can vary significantly and may impact your usage budget.

## Running the Agent

Run the agent using the following command:

```bash
python ./main.py <path_or_url_to_openapi_definition>
```

The agent accepts either:

- A local file path to your OpenAPI/Swagger specification or Postman collection
- A URL to a JSON or YAML OpenAPI/Swagger specification (URL not supported for Postman collections)

### Options

- `--destination-folder`: Specify output directory (default: ./generated-framework\_[timestamp])
- `--use-existing-framework`: Use an existing framework instead of creating a new one
- `--endpoints`: Generate framework for specific endpoints (can specify multiple)
- `--generate`: Specify what to generate (default: models_and_tests)
  - `models`: Generate only the data models
  - `models_and_first_test`: Generate data models and the first test for each endpoint
  - `models_and_tests`: Generate data models and complete test suites
- `--list-endpoints`: List the endpoints that can be used with the --endpoints flag

> **Note**: The `--endpoints`, `--generate`, `--list-endpoints`, and `--use-existing-framework` options are only available when using Swagger/OpenAPI specifications. When using Postman collections, only the `--destination-folder` parameter is fully supported.

### Examples

```bash
# Generate framework from a local file
python ./main.py api-spec.yaml
```

```bash
# Generate framework from a URL
python ./main.py https://api.example.com/swagger.json
```

```bash
# Generate list root endpoints
python ./main.py api-spec.yaml --list-endpoints
```

```bash
# Generate complete framework with all endpoints
python ./main.py api-spec.yaml
```

```bash
# Generate models and tests for specific endpoints using an existing framework
python ./main.py api-spec.yaml --use-existing-framework --destination-folder ./my-api-framework --endpoints /user /store
```

```bash
# Generate only data and service models for all endpoints
python ./main.py api-spec.yaml --generate models
```

```bash
# Generate models and first test for each endpoint in a custom folder
python ./main.py api-spec.yaml --generate models_and_first_test --destination-folder ./quick-tests
```

```bash
# Combine options to generate specific endpoints with first test only
python ./main.py api-spec.yaml --endpoints /store --generate models_and_first_test
```

The generated framework will follow the structure:

```
generated-framework_[timestamp]/    # Or the Destination Folder selected
├── src/
│   ├── base/                       # Framework base classes
│   ├── models/                     # Generated TypeScript interfaces and API service classes
│   └── tests/                      # Generated test suites
├── package.json
├── (...)
└── tsconfig.json
```

## Postman Collection Migration

The API Automation Agent can now convert your Postman collections into TypeScript automated test frameworks, preserving the structure and test logic of your collections.

### Supported Features

- Converts Postman Collection v2.0 format JSON files into a TypeScript test framework
- Maintains the original folder structure of your Postman collection
- Preserves test run order for consistent test execution
- Creates service files by grouping API routes by path
- Migrates test scripts and assertions

### Limitations

- Only supports local Postman collection files (no HTTP download support yet)
- Currently only supports Postman Collection v2.0 format
- Scripts contained in folders (rather than requests) are not processed
- Limited CLI support - only the `--destination-folder` parameter is fully supported with Postman collections

### Best Practices

The migration works best with well-structured APIs where:

- Endpoints are organized logically by resource
- Similar endpoints (e.g., /users, /users/{id}) are grouped together
- HTTP methods follow REST conventions

### Usage

```bash
# Migrate a Postman collection to TypeScript test framework
python ./main.py path/to/postman_collection.json --destination-folder ./my-api-tests
```

## Testing the Agent

To try out the agent without using your own API specification, you can use one of the following test APIs:

- [CatCafe API](https://github.com/CodingRainbowCat/CatCafeProject): Test API created by [@CodingRainbowCat](https://github.com/CodingRainbowCat) epecifically for testing the agent. You can check the repo to run it locally. It's very useful since it can be easily modified to test different scenarios.
- [Pet Store API](https://petstore.swagger.io/#/): Public test API

### Examples

**Cat Cafe**

```bash
# /adopters endpoints
python ./main.py http://localhost:3000/swagger.json --endpoints /adopters
```

**Pet Store**

```bash
# /store endpoints
python ./main.py https://petstore.swagger.io/v2/swagger.json --endpoints /store
```

These are simple and small examples that includes basic CRUD operations and are ideal for testing the agent's capabilities.
Estimated cost (with claude-sonnet-4-20250514) to run each example above: US$ ~0.3

You can combine endpoints to test larger scenarios.:

```bash
python ./main.py http://localhost:3000/swagger.json --endpoints /adopters /pet
```

Or simply run it for the whole API

```bash
python ./main.py http://localhost:3000/swagger.json
```

## Running Tests

The project includes a comprehensive test suite to ensure code quality and functionality. Here's how to run and work with the tests:

### Test Structure

- Unit tests are located in `tests/unit/`
- Integration tests are in `tests/integration/`
- Test fixtures and mocks are in `tests/fixtures/`

### Running the Test Suite

1. Install test dependencies:

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt  # Additional test dependencies
   ```

2. Run all tests:

   ```bash
   pytest
   ```

3. Run specific test categories:

   ```bash
   pytest tests/unit/  # Run only unit tests
   pytest tests/integration/  # Run only integration tests
   ```

4. Run tests with coverage report:
   ```bash
   pytest --cov=src --cov-report=term --cov-config=.coveragerc
   ```

### Test Best Practices

- All external LLM calls are mocked to keep tests fast and free of API costs
- Use the `@pytest.mark.asyncio` decorator for async tests
- Follow the naming convention: `test_<function_name>_<scenario>`
- Keep tests focused and isolated
- Use fixtures for common setup and teardown

### Writing New Tests

When adding new tests:

1. Place them in the appropriate directory based on test type
2. Use descriptive names that explain the test scenario
3. Mock external dependencies using `pytest-mock`
4. Add appropriate assertions to verify behavior
5. Consider edge cases and error scenarios

## Performance Benchmarking

This project includes a benchmark tool designed to evaluate the performance of different Large Language Models (LLMs) in generating API test frameworks using this agent. It automates running the agent against an OpenAPI specification for various LLMs and collects quantifiable metrics.

For detailed instructions on how to set up, run, and interpret the benchmark results, please refer to the [Benchmark README](./benchmarks/README.md).

## Checkpoints

The checkpoints feature allows you to save and restore the state of the framework generation process. This is useful if you need to interrupt the process and resume it later without losing progress.

### Purpose

The purpose of the checkpoints feature is to provide a way to save the current state of the framework generation process and restore it later.

### How to Use

1. **Saving State**: The state is automatically saved at various points during the framework generation process. You don't need to manually save the state.

2. **Restoring State**: If a previous run was interrupted, you will be prompted to resume the process when you run the agent again. The agent will restore the last saved state and continue from where it left off.

3. **Clearing Checkpoints**: After the framework generation process is completed successfully, the checkpoints are automatically cleared.

### Implementation

The checkpoints feature is implemented in the `src/utils/checkpoint.py` file. It uses the `shelve` module to store the state in a persistent dictionary.

#### Decorator to Functions

The `Checkpoint` class provides a `checkpoint` decorator that can be used to automatically save and restore the state of a function. This decorator can be applied to any function that you want to checkpoint.

Example:

```python
from src.utils.checkpoint import Checkpoint

class MyClass:
    def __init__(self):
        self.checkpoint = Checkpoint(self)

    @Checkpoint.checkpoint()
    def my_function(self, arg1, arg2):
        # Function logic here
        pass
```

#### For Wrapper

The `checkpoint_iter` method of the `Checkpoint` class can be used to wrap a for-loop and automatically save and restore progress. This is useful for long-running loops where you want to ensure progress is not lost.

Example:

```python
from src.utils.checkpoint import Checkpoint

class MyClass:
    def __init__(self):
        self.checkpoint = Checkpoint(self)
        self.state = {"info": []}

    def my_loop_function(self, items):
        for item in self.checkpoint.checkpoint_iter(items, "my_loop", self.state):
            self.state["info"].append(item)
         print(self.state)
```

In the example above, the `checkpoint_iter` method is used to wrap the for-loop. The `self.state` dictionary is passed as the third argument to the `checkpoint_iter` method. This dictionary needs to be in the format of a dict with a state. The iteration will start from where it left off (index) and restore the last state of the third variable.

## Contribution Guidelines

Contributions are welcome! Here's how you can help:

### Finding Tasks to Work On

We maintain a [project board](https://github.com/orgs/TestCraft-App/projects/2/views/1) to track features, enhancements, and bugs. Each task in the board includes:

- Task descriptions
- Priority
- Complexity
- Size

New contributors can check out our ["Good First Issues"](https://github.com/orgs/TestCraft-App/projects/2/views/2) view for beginner-friendly tasks to get started with.

### Contribution Process

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request to the original repo

### Reporting Issues

Found a bug or have a suggestion? Please open an issue on GitHub with:

- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment details (OS, Python version, etc.)

## Code Formatting

This project uses strict code formatting rules to maintain consistency:

- [Black](https://black.readthedocs.io/) is used as the Python code formatter
  - Line length is set to 88 characters
  - Python 3.7+ compatibility is enforced
- VS Code is configured for automatic formatting on save
- Editor settings and recommended extensions are provided in the `.vscode` directory

All Python files will be automatically formatted when you save them in VS Code with the recommended extensions installed. To manually format code, you can run:

```bash
black .
```

## Logging

The project implements a dual logging strategy:

1. **Console Output**: By default shows INFO level messages in a user-friendly format

   ```
   Generated service class for Pet endpoints
   Creating test suite for /pet/findByStatus
   ```

2. **File Logging**: Detailed DEBUG level logging with timestamps and metadata in `logs/[framework-name].log`
   ```
   2024-03-21 14:30:22,531 - generator.services - DEBUG - Initializing service class generator for Pet endpoints
   2024-03-21 14:30:22,531 - generator.services - INFO - Generated service class for Pet endpoints
   2024-03-21 14:30:23,128 - generator.tests - DEBUG - Loading OpenAPI spec for /pet/findByStatus
   2024-03-21 14:30:23,128 - generator.tests - INFO - Creating test suite for /pet/findByStatus
   ```

### Debug Options

You can control debug levels through environment variables:

1. **Application Debug**: Set `DEBUG=True` in your `.env` file to enable debug-level logging in the console output
2. **LangChain Debug**: Set `LANGCHAIN_DEBUG=True` to enable detailed logging of LangChain operations

Example `.env` configuration:

```env
DEBUG=False          # Default: False (INFO level console output)
LANGCHAIN_DEBUG=False  # Default: False (disabled)
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI and Anthropic for their AI models
- All contributors who have helped build and improve this project
