from argparse import Namespace
import logging
import os
import traceback

from dependency_injector.wiring import inject, Provide
from dotenv import load_dotenv

from src.adapters.config_adapter import ProdConfigAdapter, DevConfigAdapter
from src.adapters.processors_adapter import ProcessorsAdapter
from src.configuration.cli import CLIArgumentParser
from src.configuration.config import Config, GenerationOptions, Envs
from src.container import Container
from src.test_controller import TestController
from src.utils.checkpoint import Checkpoint
from src.utils.logger import Logger
from src.processors.swagger.endpoint_lister import EndpointLister
from src.configuration.data_sources import DataSource, get_processor_for_data_source
from src.processors.api_processor import APIProcessor


@inject
def main(
    logger: logging.Logger,
    config: Config = Provide[Container.config],
    test_controller: TestController = Provide[Container.test_controller],
):
    """Main function to orchestrate the API framework generation process."""
    try:
        logger.info("🚀 Starting the API Framework Generation Process! 🌟")

        args = CLIArgumentParser.parse_arguments()

        checkpoint = Checkpoint()

        last_namespace = checkpoint.get_last_namespace()

        def prompt_user_resume_previous_run():
            while True:
                user_input = (
                    input("Info related to a previous run was found, would you like to resume? (y/n): ")
                    .strip()
                    .lower()
                )

                if user_input in {"y", "n"}:
                    return user_input == "y"

        data_source = APIProcessor.set_data_source(args.api_definition, logger)

        def handle_unsupported_cli_args(data_source: DataSource, args: Namespace):
            if data_source == DataSource.POSTMAN and (
                args.use_existing_framework
                or args.list_endpoints
                or args.endpoints
                or (args.generate != GenerationOptions.MODELS_AND_TESTS.value)
            ):
                raise ValueError(
                    "The specified CLI arguments are not supported for the current data source. "
                    "Check the README.md document for more info."
                )

        handle_unsupported_cli_args(data_source, args)

        if last_namespace != "default" and prompt_user_resume_previous_run():
            checkpoint.restore_last_namespace()
            args.destination_folder = last_namespace

        if args.use_existing_framework and not args.destination_folder:
            raise ValueError("The destination folder parameter must be set when using an existing framework.")

        config.update(
            {
                "api_definition": args.api_definition,
                "destination_folder": args.destination_folder or config.destination_folder,
                "endpoints": args.endpoints,
                "generate": GenerationOptions(args.generate),
                "data_source": data_source,
                "use_existing_framework": args.use_existing_framework,
                "list_endpoints": args.list_endpoints,
            }
        )

        logger.info(f"\nAPI definition: {config.api_definition}")

        processor = get_processor_for_data_source(data_source, container)
        container.api_processor.override(processor)
        framework_generator = container.framework_generator()

        logger.info(f"\nAPI file path: {config.api_definition}")
        logger.info(f"Destination folder: {config.destination_folder}")
        logger.info(f"Use existing framework: {config.use_existing_framework}")
        logger.info(f"Endpoints: {', '.join(config.endpoints) if config.endpoints else 'All'}")
        logger.info(f"Generate: {config.generate}")
        logger.info(f"Model: {config.model}")
        logger.info(f"List endpoints: {config.list_endpoints}")

        if last_namespace == "default" or last_namespace != args.destination_folder:
            checkpoint.namespace = config.destination_folder
            checkpoint.save_last_namespace()
        else:
            framework_generator.restore_state(last_namespace)

        api_definitions = framework_generator.process_api_definition()

        if config.list_endpoints:
            EndpointLister.list_endpoints(api_definitions.definitions)
            logger.info("\n✅ Endpoint listing completed successfully!")
        else:
            if not config.use_existing_framework:
                framework_generator.setup_framework(api_definitions)
                framework_generator.create_env_file(api_definitions)

            framework_generator.generate(api_definitions, config.generate)
            test_files = framework_generator.run_final_checks(config.generate)

            logger.info("\n✅ Framework generation completed successfully!")

            if test_files:
                test_controller.run_tests_flow(test_files)

        checkpoint.clear()

    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
    except PermissionError as e:
        logger.error(f"❌ Permission denied: {e}")
    except ValueError as e:
        logger.error(f"❌ Invalid data: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    load_dotenv(override=True)
    env = Envs(os.getenv("ENV", "DEV").upper())

    # Initialize containers
    config_adapter = ProdConfigAdapter() if env == Envs.PROD else DevConfigAdapter()
    processors_adapter = ProcessorsAdapter(config=config_adapter.config)
    container = Container(config_adapter=config_adapter, processors_adapter=processors_adapter)

    # Wire dependencies
    container.init_resources()
    container.wire(modules=[__name__])

    Logger.configure_logger(container.config())
    logger = Logger.get_logger(__name__)

    try:
        main(logger)
    except Exception as e:
        logger.error(f"💥 A critical error occurred: {e}")
        traceback.print_exc()
