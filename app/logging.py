import logging
import threading
import traceback

import requests

from app.config import APP_VERSION, PYTHON_ANYWHERE_API, PYTHON_ANYWHERE_API_TOKEN


class CustomLogFormatter(logging.Formatter):
    def formatStack(self, stack_info: str = "") -> str:
        """Trim everything after word 'Stacktrace'."""

        if "NoneType: None\n" == stack_info:
            return ""

        stack_info_without_stacktrace = stack_info[: stack_info.find("Stacktrace")]
        return f'"\n"{"".join(stack_info_without_stacktrace)}'

    def format(self, record: logging.LogRecord):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        message = self.formatMessage(record)
        if record.levelno >= logging.ERROR:
            record.stack_info = traceback.format_exc()
            message = message + self.formatStack(record.stack_info)

        return message


class CustomLoggingHandler(logging.Handler):
    """Whenever something is logged save the same message also in remote cloud service."""

    def __init__(self, level=logging.DEBUG, user_name: str = "Nonename") -> None:
        super().__init__(level)
        self.user_name = user_name
        self.formatter = CustomLogFormatter(
            f"%(levelname)s | %(name)s | %(asctime)s | v{APP_VERSION} | %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S",
        )

    def emit(self, *args):
        msg = self.formatter.format(*args)

        headers = {
            "Content-Type": "application/json",
            "Authorization": PYTHON_ANYWHERE_API_TOKEN,
        }
        data = {"owner": self.user_name, "message": msg}
        threading.Thread(
            target=requests.post,
            kwargs={
                "url": PYTHON_ANYWHERE_API + "/log",
                "json": data,
                "headers": headers,
            },
        ).start()


def get_logger(
    name: str,
    filename: str = "logs/log.txt",
    logger_level: int = logging.DEBUG,
    f_handler_level: int = logging.ERROR,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logger_level)
    f_handler = logging.FileHandler(filename)
    f_handler.setLevel(f_handler_level)
    f_format = CustomLogFormatter(
        "%(levelname)s | %(name)s | %(asctime)s | %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S",
    )
    f_handler.setFormatter(f_format)
    logger.addHandler(f_handler)
    logger.propagate = False

    return logger


def add_event_handler(settings: dict) -> None:

    logging_handler = CustomLoggingHandler(user_name=settings["user_name"])
    logging.getLogger("__main__").addHandler(logging_handler)
    logging.getLogger("app.functions").addHandler(logging_handler)
    logging.getLogger("bot_functions").addHandler(logging_handler)
    logging.getLogger("app.decorators").addHandler(logging_handler)
    logging.getLogger("gui.windows.log_in").addHandler(logging_handler)
    logging.getLogger("gui.functions").addHandler(logging_handler)
    logging.getLogger("app.tribal_wars_bot_api").addHandler(logging_handler)
    # print(logging.root.manager.loggerDict)
