"""Interactive setup for API key and model configuration."""

import getpass
import os
import shutil
from typing import Optional
from pathlib import Path


class InteractiveSetup:
    """Handle interactive setup for API keys and model selection."""

    SUPPORTED_PROVIDERS = {
        "1": {
            "name": "Anthropic (recommended)",
            "env_key": "ANTHROPIC_API_KEY",
            "models": [
                "claude-fable-5-1",
                "claude-opus-5",
                "claude-sonnet-5",
                "claude-haiku-4-5",
            ],
            "default_model": "claude-sonnet-5",
        },
        "2": {
            "name": "OpenAI",
            "env_key": "OPENAI_API_KEY",
            "models": ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"],
            "default_model": "gpt-5.6-sol",
        },
        "3": {
            "name": "Google Generative AI",
            "env_key": "GOOGLE_API_KEY",
            "models": ["gemini-3.1-pro-preview", "gemini-3-flash", "gemini-3-pro-preview"],
            "default_model": "gemini-3-flash",
        },
        "4": {
            "name": "AWS Bedrock",
            "env_key": "AWS_ACCESS_KEY_ID",
            "additional_keys": ["AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
            "models": [
                "anthropic.claude-fable-5-1",
                "anthropic.claude-opus-5",
                "anthropic.claude-sonnet-5",
                "anthropic.claude-haiku-4-5-20251001-v1:0",
                "openai.gpt-5.6-sol",
                "openai.gpt-5.6-terra",
                "openai.gpt-5.6-luna",
                "google.gemini-3.1-pro-preview",
                "google.gemini-3-flash",
                "google.gemini-3-pro-preview",
            ],
            "default_model": "anthropic.claude-sonnet-5",
        },
    }

    @staticmethod
    def get_executable_directory() -> Path:
        """Get the directory where the executable is running from."""
        if hasattr(os.sys, "_MEIPASS"):
            return Path(os.sys.executable).parent
        else:
            return Path(os.getcwd())

    @staticmethod
    def copy_example_env() -> bool:
        """Copy example.env to .env in the executable directory."""
        exe_dir = InteractiveSetup.get_executable_directory()
        example_env_path = exe_dir / "example.env"
        env_path = exe_dir / ".env"

        if not example_env_path.exists():
            print(f"❌ Error: example.env not found in {exe_dir}")
            return False

        try:
            shutil.copy2(example_env_path, env_path)
            print("✅ Created .env file from example.env")
            return True
        except Exception as e:
            print(f"❌ Error creating .env file: {e}")
            return False

    @staticmethod
    def display_provider_menu():
        """Display the provider selection menu."""
        print("\n🤖 SELECT AI PROVIDER")
        for key, provider in InteractiveSetup.SUPPORTED_PROVIDERS.items():
            print(f"{key}. {provider['name']}")

    @staticmethod
    def get_provider_choice() -> Optional[dict]:
        """Get user's provider choice."""
        while True:
            InteractiveSetup.display_provider_menu()
            choice = input("Select provider (1-4): ").strip()

            if choice in InteractiveSetup.SUPPORTED_PROVIDERS:
                return InteractiveSetup.SUPPORTED_PROVIDERS[choice]
            else:
                print("❌ Invalid choice. Please select 1, 2, 3, or 4.")

    @staticmethod
    def display_model_menu(provider: dict):
        """Display the model selection menu for a provider."""
        print(f"\n🧠 SELECT {provider['name'].upper()} MODEL")
        for i, model in enumerate(provider["models"], 1):
            default_marker = " (recommended)" if model == provider["default_model"] else ""
            print(f"{i}. {model}{default_marker}")

    @staticmethod
    def get_model_choice(provider: dict) -> str:
        """Get user's model choice."""
        while True:
            InteractiveSetup.display_model_menu(provider)
            choice = input(
                f"Select model (1-{len(provider['models'])}), or press Enter for recommended model: "
            ).strip()

            if not choice:
                return provider["default_model"]

            try:
                index = int(choice) - 1
                if 0 <= index < len(provider["models"]):
                    return provider["models"][index]
                else:
                    print(f"❌ Invalid choice. Please select 1-{len(provider['models'])}")
            except ValueError:
                print("❌ Please enter a number.")

    @staticmethod
    def get_api_key(provider: dict, input_func=None) -> dict:
        """Get API key(s) from user. Returns dict with key names and values."""
        credentials = {}

        if provider["name"] == "AWS Bedrock":
            print(f"\n🔑 {provider['name'].upper()} AUTHENTICATION")
            print("\n📋 You can authenticate in two ways:")
            print("  1. AWS CLI (recommended) - Run 'aws configure' first")
            print("  2. Environment variables - Enter credentials below")
            print("\n💡 If you've already configured AWS CLI, press Enter to skip credential input.")
            print("   The agent will use your AWS CLI configuration automatically.")
            print("\nGet AWS credentials from: https://console.aws.amazon.com/iam/")

            if input_func is None:

                def default_input_func(prompt):
                    return getpass.getpass(prompt)

                input_func = default_input_func

            while True:
                try:
                    access_key = input_func("Enter AWS Access Key ID (or press Enter to skip): ").strip()

                    if not access_key:
                        region = input("Enter AWS Region (default: us-east-1): ").strip() or "us-east-1"
                        credentials["AWS_REGION"] = region
                        print("✅ Will use AWS CLI default credentials")
                        return credentials

                    secret_key = input_func("Enter AWS Secret Access Key: ").strip()
                    if not secret_key:
                        print("❌ Secret Access Key cannot be empty when Access Key is provided.")
                        continue

                    region = input("Enter AWS Region (default: us-east-1): ").strip() or "us-east-1"

                    credentials["AWS_ACCESS_KEY_ID"] = access_key
                    credentials["AWS_SECRET_ACCESS_KEY"] = secret_key
                    credentials["AWS_REGION"] = region
                    return credentials
                except KeyboardInterrupt:
                    print("\n❌ Setup cancelled by user.")
                    return {}
        else:
            print(f"\n🔑 ENTER {provider['name'].upper()} API KEY")
            print("Get your API key from:")
            if provider["name"] == "OpenAI":
                print("https://platform.openai.com/api-keys")
            elif provider["name"] == "Google Generative AI":
                print("https://aistudio.google.com/api-keys")
            else:
                print("https://console.anthropic.com/")
            print("\n⚠️  Your API key will be stored securely in the .env file")

            if input_func is None:

                def default_input_func(prompt):
                    return getpass.getpass(prompt)

                input_func = default_input_func

            while True:
                try:
                    api_key = input_func("Enter your API key: ").strip()
                    if api_key:
                        credentials[provider["env_key"]] = api_key
                        return credentials
                    else:
                        print("❌ API key cannot be empty.")
                except KeyboardInterrupt:
                    print("\n❌ Setup cancelled by user.")
                    return {}

    @staticmethod
    def update_env_file(provider: dict, model: str, credentials: dict) -> bool:
        """Update the .env file with the selected configuration."""
        exe_dir = InteractiveSetup.get_executable_directory()
        env_path = exe_dir / ".env"

        try:
            if env_path.exists():
                with open(env_path, "r") as f:
                    lines = f.readlines()
            else:
                lines = []

            updated_lines = []
            keys_found = {key: False for key in credentials.keys()}
            keys_found["MODEL"] = False

            for line in lines:
                line_key = line.split("=")[0] if "=" in line else ""
                if line_key in credentials:
                    updated_lines.append(f"{line_key}={credentials[line_key]}\n")
                    keys_found[line_key] = True
                elif line.startswith("MODEL="):
                    updated_lines.append(f"MODEL={model}\n")
                    keys_found["MODEL"] = True
                else:
                    updated_lines.append(line)

            # Add any missing keys
            for key, value in credentials.items():
                if not keys_found[key]:
                    updated_lines.append(f"{key}={value}\n")
            if not keys_found["MODEL"]:
                updated_lines.append(f"MODEL={model}\n")

            with open(env_path, "w") as f:
                f.writelines(updated_lines)

            print("✅ Configuration saved to .env file")
            print(f"   Provider: {provider['name']}")
            print(f"   Model: {model}")

            for key, value in credentials.items():
                if len(value) > 12:
                    masked_value = f"{value[:8]}{'*' * (len(value) - 12)}{value[-4:]}"
                elif len(value) > 8:
                    masked_value = f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"
                else:
                    masked_value = "*" * len(value)
                print(f"   {key}: {masked_value}")
            return True

        except Exception as e:
            print(f"❌ Error updating .env file: {e}")
            return False

    @staticmethod
    def run_interactive_setup(input_func=None) -> bool:
        """Run the complete interactive setup process."""
        print("\n🚀 API AUTOMATION AGENT - FIRST TIME SETUP")
        print("Welcome! Let's configure your AI provider and API key.")
        print("This will create a .env file with your configuration.")

        if not InteractiveSetup.copy_example_env():
            return False

        provider = InteractiveSetup.get_provider_choice()
        if not provider:
            return False

        model = InteractiveSetup.get_model_choice(provider)

        credentials = InteractiveSetup.get_api_key(provider, input_func)
        if not credentials:
            return False

        if InteractiveSetup.update_env_file(provider, model, credentials):
            print("\n🎉 Setup completed successfully!")
            print("You can now use the API Automation Agent.")
            print("\nTo change your configuration later, edit the .env file or delete it to run setup again.")
            return True
        else:
            return False

    @staticmethod
    def check_env_file() -> bool:
        """Check if .env file exists and has required configuration."""
        exe_dir = InteractiveSetup.get_executable_directory()
        env_path = exe_dir / ".env"

        if not env_path.exists():
            return False

        try:
            with open(env_path, "r") as f:
                content = f.read()

            has_openai = (
                "OPENAI_API_KEY=" in content
                and not content.split("OPENAI_API_KEY=")[1].split("\n")[0].strip() == ""
            )
            has_anthropic = (
                "ANTHROPIC_API_KEY=" in content
                and not content.split("ANTHROPIC_API_KEY=")[1].split("\n")[0].strip() == ""
            )
            has_google = (
                "GOOGLE_API_KEY=" in content
                and not content.split("GOOGLE_API_KEY=")[1].split("\n")[0].strip() == ""
            )
            has_aws = (
                "AWS_ACCESS_KEY_ID=" in content
                and not content.split("AWS_ACCESS_KEY_ID=")[1].split("\n")[0].strip() == ""
                and "AWS_SECRET_ACCESS_KEY=" in content
                and not content.split("AWS_SECRET_ACCESS_KEY=")[1].split("\n")[0].strip() == ""
            )

            return has_openai or has_anthropic or has_google or has_aws

        except Exception:
            return False
