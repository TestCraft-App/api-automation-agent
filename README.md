# API Automation Agent

An open-source AI Agent that automatically generates an automation framework from your OpenAPI/Swagger specification, based on the api-framework-ts-mocha template (https://github.com/damianpereira86/api-framework-ts-mocha).

## Features

- Generates type-safe service and data models
- Generates test suites for every endpoint
- Reviewes and fixes code issues and ensures code quality and best practices
- Includes code formatting and linting
- Runs tests with detailed reporting and assertions

## Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- Anthropic API key (Anthropic API key required by default), OpenAI API key or Google API key

## Installation

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

This project supports Anthropic, OpenAI and Google language models. 

### Default Model

**Claude 3.7 Sonnet** (claude-3-7-sonnet-latest) is the default and recommended model for this agentic workflow.
- Provides superior code generation and understanding
- Offers the best balance of performance and cost
- **Strongly recommended**: Other models may not provide satisfactory results for this specific use case

### Supported Models

**Anthropic**

  - Claude 3.7 Sonnet (claude-3-7-sonnet-latest)
  - Claude 3.5 Sonnet (claude-3-5-sonnet-latest)

**OpenAI**

  - GPT-4o (gpt-4o)
  - GPT-4.1 (gpt-4.1)
  - O3 (o3)
  - O4 Mini (o4-mini)

**Google**

  - Gemini 2.5 Pro Preview (gemini-2.5-pro-preview-03-25")
  - Gemini 2.5 Pro Experimiental (gemini-2.5-pro-exp-03-25)

Note: Google models are experimental for the moment, and are not recommended for a production workload.  

You can configure your preferred model in the `.env` file:

```env
MODEL=o4-mini
```

> **Important**: Before using any model, please check the current pricing and costs on the respective provider's website (Anthropic, OpenAI, or Google). Model costs can vary significantly and may impact your usage budget.

## Usage

Run the agent using the following command:

```bash
python ./main.py <path_or_url_to_openapi_definition>
```

The agent accepts either:
- A local file path to your OpenAPI/Swagger specification
- A URL to a JSON or YAML OpenAPI/Swagger specification

### Options

- `--destination-folder`: Specify output directory (default: ./generated-framework\_[timestamp])
- `--use-existing-framework`: Use an existing framework instead of creating a new one
- `--endpoints`: Generate framework for specific endpoints (can specify multiple)
- `--generate`: Specify what to generate (default: models_and_tests)
  - `models`: Generate only the data models
  - `models_and_first_test`: Generate data models and the first test for each endpoint
  - `models_and_tests`: Generate data models and complete test suites
- `--list-endpoints`: List the endpoints that can be used with the --endpoints flag.

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
Estimated cost (with claude-3-7-sonnet-latest) to run each example above: US$ ~0.1  

You can combine endpoints to test larger scenarios.:

```bash
python ./main.py http://localhost:3000/swagger.json --endpoints /adopters /pet
```

Or simply run it for the whole API

```bash
python ./main.py http://localhost:3000/swagger.json
```

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

- Anthropic, OpenAI and Google for their AI models
- All contributors who have helped build and improve this project

