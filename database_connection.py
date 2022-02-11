import pyodbc

from gui_functions import custom_error


class DataBaseConnection:
    def __init__(self) -> None:
        self.cnxn = None
        self.cursor = None

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
            pass

    def __exit__(self, exc_type, exc_value, exc_tracebac):
        if not self.cnxn:
            custom_error("Serwer jest tymczasowo niedostępny.")
            return True
        self.cnxn.commit()
        self.cnxn.close()
