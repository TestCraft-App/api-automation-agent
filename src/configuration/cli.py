import argparse
from datetime import datetime


class CLIArgumentParser:
    @staticmethod
    def parse_arguments():
        parser = argparse.ArgumentParser(description="API Framework Generation Tool")
        parser.add_argument(
            "api_definitions",
            nargs="+",
            help="One or more API definition files or URLs (space separated). Example: file1.yaml file2.json",
        )
        parser.add_argument(
            "--destination-folder",
            type=str,
            default=f"./generated/generated-framework_{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            help="Destination folder in which the files will be created (optional).",
        )
        parser.add_argument(
            "--endpoints",
            type=str,
            nargs="+",
            help=(
                "Specify one or more endpoints to generate the framework for (optional)."
                "Example: --endpoint /pets /store"
            ),
        )
        parser.add_argument(
            "--generate",
            type=str,
            choices=["models", "models_and_first_test", "models_and_tests"],
            default="models_and_tests",
            help=(
                "Specify what to generate. 'models' for models only,"
                "'models_and_first_test' for models and first test, "
                "'models_and_tests' for models and tests."
            ),
        )
        parser.add_argument(
            "--use-existing-framework",
            action="store_true",
            help="Use an existing framework instead of creating a new one.",
        )
        parser.add_argument(
            "--list-endpoints",
            help="List the endpoints that can be used with the --endpoints flag.",
            action="store_true",
        )
        return parser.parse_args()
