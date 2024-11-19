# API Automation Agent

An open-source AI Agent that automatically generates an automation framework from your OpenAPI/Swagger specification, based on the api-framework-ts-mocha template (https://github.com/damianpereira86/api-framework-ts-mocha).

## Features

- Generates type-safe service and data models
- Generates test suites for every endpoint
- Uses AI to review and fix code issues and ensure code quality and best practices
- Includes code formatting and linting
- Runs tests with detailed reporting and assertions

## Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- OpenAI API key or Anthropic API key

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/api-automation-agent.git
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

## Usage

Run the agent using the following command:

```bash
python ./main.py path/to/your/openapi.yaml
```

### Options

- `--destination-folder`: Specify output directory (default: ./generated-framework_[timestamp])
- `--endpoint`: Generate framework for a specific endpoint only
- `--generate`: Specify what to generate (default: models_and_tests)
  - `models`: Generate only the data models
  - `models_and_tests`: Generate both data models and test suites

### Example

```bash
python ./main.py api-spec.yaml --destination-folder ./my-api-client
```

The generated framework will be created in your specified destination folder.

## Testing the Agent

To try out the agent without using your own API specification, you can use the sample API definitions provided in the `api-definitions` folder. They are derived from the Pet Store API described in https://petstore.swagger.io/#/

1. Start with the Store endpoints (recommended for testing and debugging because of its size):
```bash
python ./main.py api-definitions/petstore-swagger-store.json
```

This is a simple and small API specification that includes basic CRUD operations and is ideal for testing the agent's capabilities.  

Estimated cost to run Store example: US$ ~0.1

Other available test specifications:
- `api-definitions/petstore-swagger-user.json` User endpoints
- `api-definitions/petstore-swagger-reduced.json` User and Store endpoints
- `api-definitions/petstore-swagger.json` Complete Pet Store API

Each specification varies in complexity and will generate different amounts of code and tests, affecting the total cost of execution.

## Contributing

Contributions are welcome! Here's how you can help:

### Finding Tasks to Work On

We maintain a [project board](https://github.com/users/damianpereira86/projects/1/views/1) to track features, enhancements, and bugs. Each task in the board includes:
- Task descriptions
- Priority
- Complexity
- Size

New contributors can check out our ["Good First Issues"](https://github.com/users/damianpereira86/projects/1/views/7) view for beginner-friendly tasks to get started with.

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

1. **Console Output**: User-friendly, simplified format showing only the message content
    ```
    Generated service class for Pet endpoints
    Creating test suite for /pet/findByStatus
    ```

2. **File Logging**: Detailed logging with timestamps and metadata in `logs/[framework-name].log`
    ```
    2024-03-21 14:30:22,531 - generator.services - INFO - Generated service class for Pet endpoints
    2024-03-21 14:30:23,128 - generator.tests - INFO - Creating test suite for /pet/findByStatus
    ```

The log level can be controlled through the debug flag, with DEBUG level providing more verbose output for troubleshooting.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI and Anthropic for their AI models
- The Endava Testing Discipline for inspiration and support