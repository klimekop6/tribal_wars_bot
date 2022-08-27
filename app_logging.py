import logging
import threading
import traceback

import requests

from config import LOGGING_API_TOKEN, PYTHON_ANYWHERE_LOGS


class CustomLogFormatter(logging.Formatter):
    def formatStack(self, stack_info: str = "") -> str:
        """Trim everything after word 'Stacktrace'."""

        stack_info_without_stacktrace = stack_info[: stack_info.find("Stacktrace")]
        return "".join(stack_info_without_stacktrace)

    def format(self, record: logging.LogRecord):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        message = self.formatMessage(record)
        if record.levelno >= logging.ERROR:
            record.stack_info = traceback.format_exc()
            if message[-1:] != "\n":
                message = message + "\n"
            message = message + self.formatStack(record.stack_info)
        if message[-1:] != "\n":
            message = message + "\n"

        return message


class CustomLoggingHandler(logging.Handler):
    """Whenever something is logged save the same message also in remote cloud service."""

    def __init__(self, level=logging.DEBUG, user_name: str = "Nonename") -> None:
        super().__init__(level)
        self.user_name = user_name
        self.formatter = CustomLogFormatter(
            "%(levelname)s | %(name)s | %(asctime)s | %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S",
        )

    def emit(self, *args):
        msg = self.formatter.format(*args)

        headers = {
            "Content-Type": "application/json",
            "Authorization": LOGGING_API_TOKEN,
        }
        data = {"owner": self.user_name, "message": msg}

        threading.Thread(
            target=requests.post,
            kwargs={
                "url": PYTHON_ANYWHERE_LOGS,
                "headers": headers,
                "json": data,
            },
        ).start()
