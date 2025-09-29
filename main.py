import os
import sys
import json
import yaml
import time
import logging
import traceback
import requests
from typing import List, Optional

from dotenv import load_dotenv
from dependency_injector.wiring import inject, Provide

from src.models import APIDefinition
from src.configuration.cli import CLIArgumentParser
from src.configuration.config import Config, GenerationOptions, Envs
from src.container import Container
from src.test_controller import TestController
from src.processors.swagger.endpoint_lister import EndpointLister
from src.configuration.data_sources import DataSource, get_processor_for_data_source
from src.processors.api_processor import APIProcessor
from src.utils.logger import Logger


def load_api_definition(file_path: str) -> Optional[APIDefinition]:
    """
    Load an API definition from YAML/JSON file or URL and convert to APIDefinition.
    """
    try:
        if file_path.startswith(("http://", "https://")):
            # Remote spec
            resp = requests.get(file_path, timeout=10)
            resp.raise_for_status()
            content = resp.text
            if file_path.endswith((".yaml", ".yml")):
                api_dict = yaml.safe_load(content)
            else:  # default JSON
                api_dict = resp.json()
        else:
            # Local spec
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"API definition file not found: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    print(f"⚠️ Skipping empty file: {file_path}")
                    return None
                if file_path.endswith((".yaml", ".yml")):
                    api_dict = yaml.safe_load(content)
                elif file_path.endswith(".json"):
                    api_dict = json.loads(content)
                else:
                    raise ValueError(f"Unsupported file format: {file_path}")

        # Convert dict into APIDefinition
        return APIDefinition.from_dict(api_dict)

    except Exception as e:
        print(f"❌ Error parsing {file_path}: {e}")
        return None


@inject
def main(
    logger: logging.Logger,
    config: Config = Provide[Container.config],
    test_controller: TestController = Provide[Container.test_controller],
):
    """Main orchestrator for API framework generation"""
    try:
        logger.info("🚀 Starting the API Framework Generation Process! 🌟")
        args = CLIArgumentParser.parse_arguments()

        # --- Load multiple API definitions ---
        api_definitions_list: List[APIDefinition] = []
        for path in args.api_definitions:
            api_def = load_api_definition(path)
            if api_def:
                api_definitions_list.append(api_def)
                title = getattr(api_def, "title", "Unknown")
                logger.info(f"Loaded API definition: {title}")
            else:
                logger.warning(f"Skipped file due to empty or parse error: {path}")

        if not api_definitions_list:
            raise ValueError("No valid API definitions found to process.")

        # --- Detect data source type ---
        data_sources = [APIProcessor.set_data_source(path, logger) for path in args.api_definitions]
        data_source = data_sources[0]  # assume all use same source

        # --- Validate CLI args ---
        if data_source == DataSource.POSTMAN and (
            args.use_existing_framework
            or args.list_endpoints
            or args.endpoints
            or (args.generate != GenerationOptions.MODELS_AND_TESTS.value)
        ):
            raise ValueError(
                "The specified CLI arguments are not supported for the current data source. "
                "Check the README.md for details."
            )

        # --- Update config ---
        config.update({
            "api_definitions": args.api_definitions,
            "destination_folder": args.destination_folder or config.destination_folder,
            "endpoints": args.endpoints,
            "generate": GenerationOptions(args.generate),
            "data_source": data_source,
            "use_existing_framework": args.use_existing_framework,
            "list_endpoints": args.list_endpoints,
        })

        logger.info(f"\nAPI definitions: {', '.join(config.api_definitions)}")

        # --- Initialize framework generator ---
        processor = get_processor_for_data_source(data_source, container)
        container.api_processor.override(processor)
        framework_generator = container.framework_generator()

        # --- Process & merge API definitions ---
        merged_api_definition = framework_generator.process_api_definition(api_definitions_list)

        # --- Display summary ---
        logger.info(f"\nDestination folder: {config.destination_folder}")
        logger.info(f"Use existing framework: {config.use_existing_framework}")
        logger.info(f"Endpoints: {', '.join(config.endpoints) if config.endpoints else 'All'}")
        logger.info(f"Generate: {config.generate}")
        logger.info(f"Model: {config.model}")
        logger.info(f"List endpoints: {config.list_endpoints}")

        # --- Endpoint listing ---
        if config.list_endpoints:
            EndpointLister.list_endpoints(merged_api_definition.definitions)
            logger.info("\n✅ Endpoint listing completed successfully!")
            return

        # --- Framework generation ---
        start_time = time.monotonic()
        if not config.use_existing_framework:
            framework_generator.create_env_file(merged_api_definition)
            framework_generator.setup_framework(merged_api_definition)

        framework_generator.generate(merged_api_definition, config.generate)
        test_files = framework_generator.run_final_checks(config.generate)
        end_time = time.monotonic()
        duration_seconds = round(end_time - start_time, 2)

        logger.info("\n✅ Framework generation completed successfully!")

        # --- Show metrics ---
        usage_metadata = framework_generator.get_aggregated_usage_metadata()
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = int(duration_seconds % 60)
        duration_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

        logger.info("\n📊 Generation Metrics:")
        logger.info(f"   Duration: {duration_str}")
        logger.info(f"   Input Tokens: {usage_metadata.total_input_tokens:,}")
        logger.info(f"   Output Tokens: {usage_metadata.total_output_tokens:,}")
        logger.info(f"   Total Cost (USD): ${usage_metadata.total_cost:.4f}")

        # --- Run tests ---
        if test_files:
            test_controller.run_tests_flow(test_files)

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    load_dotenv(override=True)
    env = Envs(os.getenv("ENV", "DEV").upper())

    # Initialize containers
    from src.adapters.config_adapter import ProdConfigAdapter, DevConfigAdapter
    from src.adapters.processors_adapter import ProcessorsAdapter

    config_adapter = ProdConfigAdapter() if env == Envs.PROD else DevConfigAdapter()
    processors_adapter = ProcessorsAdapter(config=config_adapter.config)
    container = Container(config_adapter=config_adapter, processors_adapter=processors_adapter)
    container.init_resources()
    container.wire(modules=[__name__])

    Logger.configure_logger(container.config())
    logger = Logger.get_logger(__name__)

    try:
        main(logger)
    except Exception as e:
        logger.error(f"💥 Critical error: {e}")
        traceback.print_exc()
