"""Interactive setup for API key and model configuration."""

import os
import shutil
from typing import Optional, Tuple
from pathlib import Path


class InteractiveSetup:
    """Handle interactive setup for API keys and model selection."""

    SUPPORTED_PROVIDERS = {
        "1": {
            "name": "OpenAI",
            "env_key": "OPENAI_API_KEY",
            "models": ["gpt-4o", "gpt-4.1", "gpt-5", "o3", "o4-mini"],
            "default_model": "gpt-4o",
        },
        "2": {
            "name": "Anthropic",
            "env_key": "ANTHROPIC_API_KEY",
            "models": ["claude-3-5-sonnet-latest", "claude-3-7-sonnet-latest", "claude-sonnet-4-20250514"],
            "default_model": "claude-sonnet-4-20250514",
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
            print(f"✅ Created .env file from example.env")
            return True
        except Exception as e:
            print(f"❌ Error creating .env file: {e}")
            return False

    @staticmethod
    def display_provider_menu():
        """Display the provider selection menu."""
        print("\n" + "=" * 60)
        print("🤖 SELECT AI PROVIDER")
        print("=" * 60)
        for key, provider in InteractiveSetup.SUPPORTED_PROVIDERS.items():
            print(f"{key}. {provider['name']}")
        print("=" * 60)

    @staticmethod
    def get_provider_choice() -> Optional[dict]:
        """Get user's provider choice."""
        while True:
            InteractiveSetup.display_provider_menu()
            choice = input("Select provider (1-2): ").strip()

            if choice in InteractiveSetup.SUPPORTED_PROVIDERS:
                return InteractiveSetup.SUPPORTED_PROVIDERS[choice]
            else:
                print("❌ Invalid choice. Please select 1 or 2.")

    @staticmethod
    def display_model_menu(provider: dict):
        """Display the model selection menu for a provider."""
        print(f"\n🧠 SELECT {provider['name'].upper()} MODEL")
        print("=" * 60)
        for i, model in enumerate(provider["models"], 1):
            default_marker = " (recommended)" if model == provider["default_model"] else ""
            print(f"{i}. {model}{default_marker}")
        print("=" * 60)

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
    def get_api_key(provider: dict) -> str:
        """Get API key from user."""
        print(f"\n🔑 ENTER {provider['name'].upper()} API KEY")
        print("=" * 60)
        print(f"Get your API key from:")
        if provider["name"] == "OpenAI":
            print("https://platform.openai.com/api-keys")
        else:
            print("https://console.anthropic.com/")
        print("=" * 60)

        while True:
            api_key = input("Enter your API key: ").strip()
            if api_key:
                return api_key
            else:
                print("❌ API key cannot be empty.")

    @staticmethod
    def update_env_file(provider: dict, model: str, api_key: str) -> bool:
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
            api_key_found = False
            model_found = False

            for line in lines:
                if line.startswith(provider["env_key"]):
                    updated_lines.append(f"{provider['env_key']}={api_key}\n")
                    api_key_found = True
                elif line.startswith("MODEL="):
                    updated_lines.append(f"MODEL={model}\n")
                    model_found = True
                else:
                    updated_lines.append(line)

            if not api_key_found:
                updated_lines.append(f"{provider['env_key']}={api_key}\n")
            if not model_found:
                updated_lines.append(f"MODEL={model}\n")

            with open(env_path, "w") as f:
                f.writelines(updated_lines)

            print(f"✅ Configuration saved to .env file")
            print(f"   Provider: {provider['name']}")
            print(f"   Model: {model}")
            print(f"   API Key: {'*' * (len(api_key) - 4)}{api_key[-4:]}")
            return True

        except Exception as e:
            print(f"❌ Error updating .env file: {e}")
            return False

    @staticmethod
    def run_interactive_setup() -> bool:
        """Run the complete interactive setup process."""
        print("\n🚀 API AUTOMATION AGENT - FIRST TIME SETUP")
        print("=" * 60)
        print("Welcome! Let's configure your AI provider and API key.")
        print("This will create a .env file with your configuration.")

        if not InteractiveSetup.copy_example_env():
            return False

        provider = InteractiveSetup.get_provider_choice()
        if not provider:
            return False

        model = InteractiveSetup.get_model_choice(provider)

        api_key = InteractiveSetup.get_api_key(provider)

        if InteractiveSetup.update_env_file(provider, model, api_key):
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

            return has_openai or has_anthropic

        except Exception:
            return False
