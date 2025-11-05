<div align="center">

# API Automation Agent
`AI-powered tool that generates production-ready test automation frameworks from OpenAPI specifications and Postman collections`
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![GitHub Issues](https://img.shields.io/github/issues/TestCraft-App/api-automation-agent)](https://github.com/TestCraft-App/api-automation-agent/issues)
[![GitHub Stars](https://img.shields.io/github/stars/TestCraft-App/api-automation-agent)](https://github.com/TestCraft-App/api-automation-agent/stargazers)



[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Documentation](#documentation) • [Contributing](#contributing)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
  - [Standalone Executable](#standalone-executable)
  - [Manual Installation](#manual-installation)
- [Usage](#usage)
  - [Basic Commands](#basic-commands)
  - [Command-Line Options](#command-line-options)
  - [Examples](#examples)
- [LLM Configuration](#llm-configuration)
- [Postman Collections](#postman-collections)
- [Advanced Features](#advanced-features)
  - [Checkpoints](#checkpoints)
  - [Performance Benchmarking](#performance-benchmarking)
- [Development](#development)
  - [Running Tests](#running-tests)
  - [Code Formatting](#code-formatting)
  - [Logging](#logging)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

API Automation Agent is an open-source tool that automatically generates comprehensive test automation frameworks from API specifications. Built on the [api-framework-ts-mocha](https://github.com/damianpereira86/api-framework-ts-mocha) template, it uses AI to eliminate manual setup and boilerplate code generation.

### Key Benefits

| Traditional Approach | API Automation Agent |
|---------------------|---------------------|
| Hours of manual framework setup | Minutes to generate complete framework |
| Manual test case writing | AI-generated test suites with assertions |
| Vendor lock-in with proprietary tools | Open-source, portable framework |
| Inconsistent code quality | Built-in best practices and linting |

---

## Features

### Code Generation
- Type-safe TypeScript interfaces and data models
- Service classes for all API endpoints
- Comprehensive test suites with Mocha and Chai
- ESLint and Prettier configuration included

### Quality Assurance
- Automatic code review and issue detection
- Best practices enforcement
- Detailed test reporting with assertions
- Code formatting and linting built-in

### Flexibility
- Generate complete frameworks or specific endpoints
- Update existing frameworks incrementally
- Support for OpenAPI 2.0/3.0 and Swagger specifications
- Postman collection migration to open-source framework

---

## Installation

### Prerequisites

| Requirement | Version | Notes |
|------------|---------|-------|
| **Node.js** | 18+ | Required for generated framework execution |
| **Python** | 3.8+ | Required for agent execution |
| **API Key** | - | OpenAI or Anthropic (Anthropic required by default) |

### Standalone Executable

Download the pre-built executable for your platform:

<table>
<thead>
<tr>
<th>Platform</th>
<th>Download</th>
<th>Requirements</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Windows</strong></td>
<td><a href="https://github.com/TestCraft-App/api-automation-agent/releases">api-agent-windows.zip</a></td>
<td>Windows 7 or higher</td>
</tr>
<tr>
<td><strong>macOS</strong></td>
<td><a href="https://github.com/TestCraft-App/api-automation-agent/releases">api-agent-macos.tar.gz</a></td>
<td>macOS 10.14 or higher</td>
</tr>
</tbody>
</table>

#### Windows Setup

```cmd
1. Download api-agent-windows.zip
2. Extract the archive
3. Follow the USAGE-GUIDE.txt instructions
4. Run: api-agent.exe path/to/spec.yaml
```

#### macOS Setup

```bash
# Download and extract api-agent-macos.tar.gz
chmod +x api-agent
./api-agent path/to/spec.yaml
```

### Manual Installation

For development or customization:

```bash
# Clone the repository
git clone https://github.com/TestCraft-App/api-automation-agent.git
cd api-automation-agent

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
cp example.env .env
```

Edit `.env` with your API keys:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
MODEL=claude-haiku-4-5-20251001
```

---

## Usage

### Basic Commands

```bash
# Generate from local file
./api-agent api-spec.yaml

# Generate from URL (OpenAPI only)
./api-agent https://api.example.com/swagger.json

# List available endpoints
./api-agent api-spec.yaml --list-endpoints
```

If using manual installation, replace `./api-agent` with `python main.py`.

### Command-Line Options

| Option | Description | Supported Sources |
|--------|-------------|-------------------|
| `--destination-folder` | Specify output directory | All |
| `--use-existing-framework` | Update existing framework instead of creating new one | OpenAPI/Swagger |
| `--endpoints` | Generate specific endpoints (space-separated) | OpenAPI/Swagger |
| `--generate` | Control generation scope (see table below) | OpenAPI/Swagger |
| `--list-endpoints` | Display available endpoints | OpenAPI/Swagger |

#### Generation Modes

| Mode | Description | Generated Files |
|------|-------------|----------------|
| `models` | Data models and service classes only | Interfaces, API clients |
| `models_and_first_test` | Models plus one test per endpoint | Interfaces, API clients, sample tests |
| `models_and_tests` | Complete framework (default) | Full test suite with all assertions |

### Examples

<details>
<summary><strong>Generate Complete Framework</strong></summary>

```bash
./api-agent api-spec.yaml
```

Creates a complete framework with all endpoints and tests in `generated-framework_[timestamp]/`

</details>

<details>
<summary><strong>Generate Specific Endpoints</strong></summary>

```bash
./api-agent api-spec.yaml --endpoints /user /store
```

Generates framework for only `/user` and `/store` endpoints.

</details>

<details>
<summary><strong>Update Existing Framework</strong></summary>

```bash
./api-agent api-spec.yaml \
  --use-existing-framework \
  --destination-folder ./my-api-framework \
  --endpoints /products
```

Adds `/products` endpoint to existing framework without regenerating everything.

</details>

<details>
<summary><strong>Generate Models Only</strong></summary>

```bash
./api-agent api-spec.yaml --generate models
```

Creates only TypeScript interfaces and service classes, useful for API clients.

</details>

<details>
<summary><strong>Custom Output Directory</strong></summary>

```bash
./api-agent api-spec.yaml \
  --destination-folder ./my-tests \
  --endpoints /store \
  --generate models_and_first_test
```

Generates store endpoint with sample tests in specified directory.

</details>

### Generated Framework Structure

```
generated-framework_[timestamp]/
├── src/
│   ├── base/                  # Framework core classes
│   │   ├── BaseTest.ts
│   │   └── ApiClient.ts
│   ├── models/                # Generated TypeScript interfaces and services
│   │   ├── User.ts
│   │   ├── UserService.ts
│   │   └── ...
│   └── tests/                 # Test suites
│       ├── user.test.ts
│       └── ...
├── package.json
├── tsconfig.json
├── .eslintrc.json
└── .prettierrc.json
```

---

## LLM Configuration

### Supported Models

The agent supports multiple Large Language Models with varying performance characteristics.

#### Anthropic Claude

<table>
<thead>
<tr>
<th>Model</th>
<th>Model ID</th>
<th>Best For</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Claude Haiku 4.5</strong> (Default)</td>
<td><code>claude-haiku-4-5-20251001</code></td>
<td>Balanced performance, speed, and cost</td>
</tr>
<tr>
<td><strong>Claude Sonnet 4.5</strong> (Recommended for complex APIs)</td>
<td><code>claude-sonnet-4-5-20250929</code></td>
<td>Highest quality output, complex specifications</td>
</tr>
<tr>
<td>Claude Sonnet 4</td>
<td><code>claude-sonnet-4-20250514</code></td>
<td>Standard quality tasks</td>
</tr>
<tr>
<td>Claude Sonnet 3.7</td>
<td><code>claude-3-7-sonnet-latest</code></td>
<td>Legacy support</td>
</tr>
<tr>
<td>Claude Sonnet 3.5</td>
<td><code>claude-3-5-sonnet-latest</code></td>
<td>Legacy support</td>
</tr>
</tbody>
</table>

#### OpenAI Models

<table>
<thead>
<tr>
<th>Model</th>
<th>Model ID</th>
<th>Best For</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>GPT-5</strong></td>
<td><code>gpt-5</code></td>
<td>Latest capabilities</td>
</tr>
<tr>
<td>GPT-4o</td>
<td><code>gpt-4o</code></td>
<td>Optimized performance</td>
</tr>
<tr>
<td>GPT-4.1</td>
<td><code>gpt-4.1</code></td>
<td>Standard tasks</td>
</tr>
<tr>
<td>O3</td>
<td><code>o3</code></td>
<td>Advanced reasoning</td>
</tr>
</tbody>
</table>

### Configuration

Set your preferred model in `.env`:

```env
MODEL=claude-haiku-4-5-20251001
```

> **Important**: Check current pricing at [Anthropic](https://www.anthropic.com/pricing) or [OpenAI](https://openai.com/pricing) before running generations. Model costs vary significantly.

### Model Recommendations

- **Start with Claude Haiku 4.5**: Best balance for most use cases
- **Use Claude Sonnet 4.5** for:
  - Large API specifications (50+ endpoints)
  - Complex nested data structures
  - High-quality output requirements
- **Consider GPT-5** if you prefer OpenAI's ecosystem

---

## Postman Collections

### Migration to Open Source

Convert Postman collections to TypeScript test frameworks.

#### Supported Features

- Postman Collection v2.0 format
- Preserves folder structure and test run order
- Migrates test scripts and assertions
- Groups API routes by path for service organization

#### Limitations

| Feature | Status | Notes |
|---------|--------|-------|
| HTTP URL download | Not supported | Use local files only |
| Collection formats | v2.0 only | Export as v2.0 from Postman |
| Folder-level scripts | Not processed | Move scripts to request level |
| CLI options | Limited | Only `--destination-folder` supported |

#### Best Practices

For optimal results:
- Organize endpoints logically by resource
- Group related endpoints together (`/users`, `/users/{id}`)
- Use standard REST conventions for HTTP methods
- Place test scripts at request level, not folder level

#### Usage

```bash
./api-agent path/to/postman_collection.json --destination-folder ./migrated-tests
```

Generated structure follows the same pattern as OpenAPI-generated frameworks.

---

## Advanced Features

### Checkpoints

The agent automatically saves progress during long-running operations, allowing you to resume if interrupted.

#### How It Works

1. **Automatic Saving**: State is saved at key points during generation
2. **Resume on Restart**: Agent detects incomplete runs and prompts to resume
3. **Auto-Cleanup**: Checkpoints are cleared on successful completion

#### Implementation

Checkpoints are managed transparently. No configuration required.

For developers extending the agent, use the checkpoint decorator:

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

For long-running loops:

```python
def my_loop_function(self, items):
    for item in self.checkpoint.checkpoint_iter(items, "my_loop", self.state):
        self.state["info"].append(item)
```

### Performance Benchmarking

The project includes tools to evaluate LLM performance across different models.

See [benchmarks/README.md](./benchmarks/README.md) for detailed instructions on:
- Running benchmarks
- Comparing model performance
- Analyzing cost vs. quality tradeoffs
- Interpreting results

---

## Development

### Running Tests

The project uses pytest for comprehensive unit and integration testing.

#### Test Structure

```
tests/
├── unit/              # Unit tests
├── integration/       # Integration tests
└── fixtures/          # Test data and mocks
```

#### Commands

```bash
# Install test dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Generate coverage report
pytest --cov=src --cov-report=term --cov-config=.coveragerc
```

#### Test Guidelines

- All external LLM calls are mocked (no API costs during testing)
- Use `@pytest.mark.asyncio` for async tests
- Follow naming convention: `test_<function_name>_<scenario>`
- Keep tests focused and isolated
- Use fixtures for common setup

#### Writing Tests

When adding new tests:

1. Place in appropriate directory (`unit/` or `integration/`)
2. Use descriptive names explaining the scenario
3. Mock external dependencies with `pytest-mock`
4. Include assertions for expected behavior
5. Consider edge cases and error scenarios

### Code Formatting

The project enforces strict formatting for consistency:

- **Formatter**: Black (88 character line length)
- **Python Version**: 3.7+ compatibility
- **Auto-format**: On save in VS Code

#### Manual Formatting

```bash
black .
```

Configuration is provided in `.vscode/` for automatic formatting with recommended extensions.

### Logging

Dual logging strategy for debugging and production use:

#### Console Output

INFO-level messages in user-friendly format:

```
Generated service class for Pet endpoints
Creating test suite for /pet/findByStatus
```

#### File Logging

DEBUG-level logs with timestamps in `logs/[framework-name].log`:

```
2024-03-21 14:30:22,531 - generator.services - DEBUG - Initializing service class generator
2024-03-21 14:30:22,531 - generator.services - INFO - Generated service class for Pet
```

#### Debug Configuration

Control debug levels via environment variables:

```env
DEBUG=False                # Console debug output (default: False)
LANGCHAIN_DEBUG=False      # LangChain operation logging (default: False)
```

Set `DEBUG=True` for verbose console output during development.

---

## Contributing

Contributions are welcome. We maintain a [project board](https://github.com/orgs/TestCraft-App/projects/2/views/1) with tracked tasks.

### Finding Tasks

- **Project Board**: Features, enhancements, and bugs with priorities
- **Good First Issues**: [Beginner-friendly tasks](https://github.com/orgs/TestCraft-App/projects/2/views/2)
- Each task includes description, priority, complexity, and size

### Contribution Process

```bash
# 1. Fork the repository

# 2. Create a feature branch
git checkout -b feature/your-feature-name

# 3. Make changes and test
pytest
black .

# 4. Commit with clear messages
git commit -m "Add feature: description"

# 5. Push and create Pull Request
git push origin feature/your-feature-name
```

### Pull Request Guidelines

- Include clear description of changes
- Add tests for new functionality
- Ensure all tests pass
- Follow existing code style
- Update documentation if needed

### Reporting Issues

When reporting bugs or suggesting features:

- Use clear, descriptive titles
- Provide reproduction steps for bugs
- Include expected vs. actual behavior
- Add environment details (OS, Python version, etc.)

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

## Resources

- **Documentation**: [Project Wiki](https://github.com/TestCraft-App/api-automation-agent/wiki)
- **Issue Tracker**: [GitHub Issues](https://github.com/TestCraft-App/api-automation-agent/issues)
- **Project Board**: [Development Roadmap](https://github.com/orgs/TestCraft-App/projects/2/views/1)
- **Base Template**: [api-framework-ts-mocha](https://github.com/damianpereira86/api-framework-ts-mocha)

---

<div align="center">

**[⬆ Back to Top](#api-automation-agent)**

Made with precision by the TestCraft community

</div>
