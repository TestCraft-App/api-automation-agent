import logging
import os
import sys
from typing import List

from ..configuration.config import Config


class Logger:
    @staticmethod
    def configure_logger(config: Config):
        log_level = logging.DEBUG if config.debug else logging.INFO

        # Default formats
        stdout_format = "%(message)s"
        file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Handlers
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.DEBUG if config.debug else logging.INFO)
        stdout_handler.setFormatter(logging.Formatter(stdout_format))

        base_log_folder = "logs"
        # Use only the last part of the destination_folder for the log file name
        # e.g., if destination_folder is "out/run1", log file is "logs/run1.log"
        log_file_name = config.destination_folder.replace("\\", "/").split("/")[-1] + ".log"
        full_log_path = os.path.join(base_log_folder, log_file_name)

        # Ensure the directory for the log file exists
        os.makedirs(os.path.dirname(full_log_path), exist_ok=True)

        file_handler = MultilineFileHandler(full_log_path)
        file_handler.setLevel(logging.DEBUG)  # Log everything to file by default
        file_handler.setFormatter(logging.Formatter(file_format))

        logging.basicConfig(
            format="%(message)s",  # This format is for basicConfig, handlers have their own
            level=log_level,  # Root logger level
            handlers=[stdout_handler, file_handler],
        )
        logging.getLogger("httpx").setLevel(logging.WARNING)

    @staticmethod
    def get_logger(name: str):
        return logging.getLogger(name)


class MultilineFileHandler(logging.FileHandler):
    def __init__(self, filename, mode="a", encoding="utf-8", delay=False):
        super().__init__(filename, mode, encoding, delay)

    def emit(self, record):
        try:
            if not isinstance(record.msg, str):
                record.msg = str(record.msg)

            messages: List[str] = [message for message in record.msg.split("\n") if message.strip()]

            if not messages:
                return

            for message in messages:
                new_record = logging.makeLogRecord(record.__dict__)
                new_record.msg = message
                super().emit(new_record)
        except Exception:
            self.handleError(record)
