import logging
import os
import sys
from typing import List

from src.configuration.config import Config


class Logger:
    @staticmethod
    def configure_logger(config: Config):
        log_level = logging.DEBUG if config.debug else logging.INFO

        # Default formats
        stdout_format = "%(message)s"
        file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Handlers
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(log_level)
        stdout_handler.setFormatter(logging.Formatter(stdout_format))

        log_folder = "logs/"
        os.makedirs(os.path.dirname(log_folder), exist_ok=True)
        file_handler = MultilineFileHandler(log_folder + config.destination_folder.split("/")[-1] + ".log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(file_format))

        logging.basicConfig(
            format="%(message)s",
            level=logging.DEBUG,
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
