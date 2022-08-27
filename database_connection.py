import logging

import pyodbc

from app_logging import CustomLogFormatter
from config import DB_CONNECTION, DB_DATABASE, DB_PASSWORD, DB_USERNAME
from gui_functions import custom_error

logger = logging.getLogger(__name__)
f_handler = logging.FileHandler("logs/log.txt")
f_format = CustomLogFormatter(
    "%(levelname)s | %(name)s | %(asctime)s %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
)
f_handler.setFormatter(f_format)
f_handler.setLevel(logging.ERROR)
logger.addHandler(f_handler)
logger.propagate = False


class DataBaseConnection:
    def __init__(self, ignore_erros: bool = False) -> None:
        self.cnxn = None
        self.cursor = None
        self.ignore_errors = ignore_erros

    def __enter__(self):
        try:
            self.cnxn = pyodbc.connect(
                f"""DRIVER={{ODBC Driver 17 for SQL Server}};
                                        SERVER={DB_CONNECTION};
                                        DATABASE={DB_DATABASE};
                                        UID={DB_USERNAME};
                                        PWD={DB_PASSWORD}""",
                timeout=3,
            )
            self.cursor = self.cnxn.cursor()
            return self.cursor
        except pyodbc.OperationalError as error:
            logger.error("database_connection error", exc_info=True)
            return False

    def __exit__(self, exc_type, exc_value, exc_tracebac):
        if exc_value:
            logger.error(f"{exc_type}, {exc_value}, {exc_tracebac}")
        if self.ignore_errors and not self.cnxn:
            return True
        if not self.cnxn:
            custom_error("Serwer jest tymczasowo niedostępny.")
            return True
        self.cnxn.commit()
        self.cnxn.close()


def get_user_data(settings: dict, update: bool = False) -> dict:
    db_answer = None
    user_data = None
    with DataBaseConnection() as cursor:
        cursor.execute(
            "SELECT * FROM konta_plemiona WHERE user_name='"
            + settings["user_name"]
            + "' AND password='"
            + settings["user_password"]
            + "'"
        )
        db_answer = cursor.fetchone()
        if db_answer:
            user_data = {
                key[0]: value for key, value in zip(cursor.description, db_answer)
            }

    if update:
        return user_data

    return db_answer, user_data
