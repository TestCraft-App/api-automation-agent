# API Automation Agent - Cross-Platform Usage Guide

## 🚀 Quick Start

### Prerequisites

- **Windows 7+ or macOS 10.14+**
- **Node.js** (Download from [nodejs.org](https://nodejs.org/))
- **API Key** (OpenAI or Anthropic)
- **Internet connection**

### Download and Setup

#### Windows

1. Download `api-automation-agent-windows.zip` from the releases page
2. Extract the ZIP file to a folder
3. Open Command Prompt or PowerShell in that folder

#### macOS

1. Download `api-automation-agent-macos.tar.gz` from the releases page
2. Extract the archive:
   ```bash
   tar -xzf api-automation-agent-macos.tar.gz
   cd api-automation-agent-macos
   ```
3. Make the executable file runnable (if needed):
   ```bash
   chmod +x api-automation-agent
   ```

### Configure API Key

#### Windows

1. Copy `example.env` to `.env` in the same folder as the executable:
   ```cmd
   copy example.env .env
   ```
2. Open `.env` in Notepad or any text editor
3. Add your API key (see below)

#### macOS

1. Copy the example environment file:
   ```bash
   cp example.env .env
   ```
2. Edit `.env` with your preferred editor:
   ```bash
   nano .env  # or use any text editor like TextEdit, VS Code, etc.
   ```
3. Add your API key (see below)

#### API Key Configuration (Both Platforms)

Add one of these to your `.env` file:

```env
# For OpenAI (ChatGPT)
OPENAI_API_KEY=your_openai_api_key_here

# OR for Anthropic (Claude)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Choose your preferred model
MODEL=claude-sonnet-4-20250514  # or gpt-4, gpt-3.5-turbo, etc.
```

## 📖 Basic Usage

### Display Help

#### Windows

```cmd
api-automation-agent.exe --help
```

#### macOS

```bash
./api-automation-agent --help
```

### Generate API Framework

#### Windows

```cmd
api-automation-agent.exe path/to/swagger.json
api-automation-agent.exe https://api.example.com/swagger.json
```

#### macOS

```bash
./api-automation-agent path/to/swagger.json
./api-automation-agent https://api.example.com/swagger.json
```

### Advanced Options

#### Generate for Specific Endpoints

```bash
# Windows
api-automation-agent.exe swagger.json --endpoints /users /orders

# macOS
./api-automation-agent swagger.json --endpoints /users /orders
```

#### Custom Output Directory

```bash
# Windows
api-automation-agent.exe swagger.json --destination-folder ./my-tests

# macOS
./api-automation-agent swagger.json --destination-folder ./my-tests
```

#### List Available Endpoints

```bash
# Windows
api-automation-agent.exe swagger.json --list-endpoints

# macOS
./api-automation-agent swagger.json --list-endpoints
```

## 🛠️ Generated Framework

The tool creates a TypeScript API testing framework with:

- **Models**: TypeScript interfaces for your API
- **Tests**: Ready-to-run API tests
- **Configuration**: Pre-configured test environment

### Running Generated Tests

Navigate to the generated framework folder and install dependencies:

#### Windows

```cmd
cd generated-framework_*
npm install
npm test
```

#### macOS

```bash
cd generated-framework_*/
npm install
npm test
```

### Available npm Scripts

- `npm test` - Run all tests
- `npm run smoke` - Run smoke tests only
- `npm run regression` - Run regression tests only
- `npm run lint` - Check code style
- `npm run prettify` - Format code

## 🔧 Troubleshooting

### Node.js Not Found

**Problem**: "node is not recognized" or "command not found"

**Solution**:

1. Install Node.js from [nodejs.org](https://nodejs.org/)
2. Restart your terminal/command prompt
3. Verify installation: `node --version`

### Permission Denied (macOS)

**Problem**: Permission denied when running the executable

**Solution**:

```bash
chmod +x api-automation-agent
```

### API Key Issues

**Problem**: Authentication or API errors

**Solutions**:

- Verify your API key is correct in the `.env` file
- Make sure there are no extra spaces or quotes around the key
- Check that your API key has sufficient permissions/credits
- Ensure the `.env` file is in the same folder as the executable

### Framework Generation Fails

**Problem**: "No models generated" or similar errors

**Solutions**:

- Verify your API definition file is valid JSON/YAML
- Check that the API definition URL is accessible
- Ensure your internet connection is working
- Try with a different API definition file

## 📁 File Structure

### Windows Distribution

```
api-automation-agent-windows/
├── api-automation-agent.exe    # Main executable
├── example.env                 # Environment template
├── README.md                   # Basic documentation
└── USAGE-GUIDE.md             # This guide
```

### macOS Distribution

```
api-automation-agent-macos/
├── api-automation-agent        # Main executable
├── example.env                 # Environment template
├── README.md                   # Basic documentation
└── USAGE-GUIDE.md             # This guide
```

### Generated Framework Structure

```
generated-framework_*/
├── src/
│   ├── models/                 # TypeScript models
│   ├── tests/                  # API tests
│   └── base/                   # Base classes
├── package.json               # Node.js dependencies
├── tsconfig.json              # TypeScript configuration
└── .env                       # Environment variables
```

## 🌐 Support

For issues, updates, and documentation:

- **GitHub**: [TestCraft-App/api-automation-agent](https://github.com/TestCraft-App/api-automation-agent)
- **Releases**: Check for the latest version
- **Issues**: Report bugs or request features

---

**Happy Testing! 🧪✨**

````

#### Generate framework for specific endpoints:

```cmd
api-automation-agent.exe --destination-folder my-framework --endpoints /pets /users
````

#### Generate with different options:

```cmd
# Models only
api-automation-agent.exe --generate models --destination-folder my-framework

# Models and first test
api-automation-agent.exe --generate models_and_first_test --destination-folder my-framework

# Models and all tests
api-automation-agent.exe --generate models_and_tests --destination-folder my-framework
```

### Example Complete Command:

```cmd
api-automation-agent.exe --destination-folder my-pet-store-tests --endpoints /pets /store --generate models_and_tests
```

### Troubleshooting

1. **"Missing API key" error:**

   - Make sure you have a `.env` file in the same folder as the executable
   - Check that your API key is correctly formatted in the `.env` file

2. **"Internet connection" error:**

   - The tool requires internet to communicate with AI APIs
   - Check your internet connection

3. **"Permission denied" error:**
   - Make sure you're running the command prompt as an administrator
   - Or try running from a folder where you have write permissions

### File Structure After Generation:

```
your-folder/
├── api-automation-agent.exe
├── .env
└── my-api-framework/          (generated framework)
    ├── package.json
    ├── src/
    ├── tests/
    └── ...
```

### Need Help?

Run `api-automation-agent.exe --help` for all available options and parameters.
