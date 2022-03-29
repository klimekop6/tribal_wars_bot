import pyodbc

from gui_functions import custom_error


class DataBaseConnection:
    def __init__(self, ignore_erros: bool = False) -> None:
        self.cnxn = None
        self.cursor = None
        self.ignore_errors = ignore_erros

    def __enter__(self):
        try:
            self.cnxn = pyodbc.connect(
                """DRIVER={ODBC Driver 17 for SQL Server};
                                        SERVER=***REMOVED***;
                                        DATABASE=Plemiona;
                                        UID=***REMOVED***;
                                        PWD=***REMOVED***""",
                timeout=3,
            )
            self.cursor = self.cnxn.cursor()
            return self.cursor
        except pyodbc.OperationalError:
            return False

    def __exit__(self, exc_type, exc_value, exc_tracebac):
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
