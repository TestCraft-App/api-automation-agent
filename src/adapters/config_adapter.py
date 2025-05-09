import os
from datetime import datetime

from dependency_injector import containers, providers
from dotenv import load_dotenv
from langchain_core.globals import set_debug

from ..configuration.config import Config, Envs
from ..configuration.models import Model


class BaseConfigAdapter(containers.DeclarativeContainer):
    """Configuration adapter for environment-dependent settings."""

    @staticmethod
    def get_base_config(env: Envs) -> Config:
        """Generates a configuration object based on the environment."""
        load_dotenv(override=True)
        config = Config(env=env)
        config.model = Model(os.getenv("MODEL", Model.CLAUDE_SONNET_3_7.value))
        config.debug = os.getenv("DEBUG", "False").title() == "True"
        config.langchain_debug = os.getenv("LANGCHAIN_DEBUG", "False").title() == "True"
        config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        config.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        config.destination_folder = os.getenv(
            "DESTINATION_FOLDER",
            f"./generated/generated-framework_{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        )

        set_debug(config.langchain_debug)
        return config


class DevConfigAdapter(BaseConfigAdapter):
    config = providers.Singleton(BaseConfigAdapter.get_base_config, Envs.DEV)


class ProdConfigAdapter(BaseConfigAdapter):
    config = providers.Singleton(BaseConfigAdapter.get_base_config, Envs.PROD)
