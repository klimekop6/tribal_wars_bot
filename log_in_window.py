import tkinter as tk
import uuid

import ttkbootstrap as ttk

from database_connection import DataBaseConnection
from gui_functions import center, custom_error, get_pos, if_paid
from register_window import RegisterWindow


class LogInWindow:
    def __init__(self, main_window, settings: dict) -> None:
        settings["logged"] = False
        if "user_password" in settings:
            row = None
            with DataBaseConnection() as cursor:
                cursor.execute(
                    "SELECT * FROM Konta_Plemiona WHERE UserName='"
                    + settings["user_name"]
                    + "' AND Password='"
                    + settings["user_password"]
                    + "'"
                )
                row = cursor.fetchone()
            if not row:
                custom_error(message="Automatyczne logowanie nie powiodło się.")
            elif not if_paid(str(row[5])):
                custom_error(message="Ważność konta wygasła.")
            elif row[6]:
                custom_error(message="Konto jest już obecnie w użyciu.")
            else:
                email_address = main_window.entries_content["notifications"][
                    "email_address"
                ].get()
                if not email_address or email_address == "0":
                    main_window.entries_content["notifications"]["email_address"].set(
                        row[2]
                    )
                main_window.verified_email = row[10]
                if not row[10]:
                    main_window.verification_code = row[11]
                settings["account_expire_time"] = str(row[5])
                main_window.acc_expire_time.config(
                    text=f'Konto ważne do {settings["account_expire_time"]}'
                )
                settings["logged"] = True
                main_window.master.deiconify()
                center(main_window.master)
                main_window.master.attributes("-alpha", 1.0)
                self.update_running_status(settings=settings, main_window=main_window)
                return

        self.master = tk.Toplevel(borderwidth=1, relief="groove")
        self.master.overrideredirect(True)
        self.master.resizable(0, 0)
        self.master.attributes("-topmost", 1)

        self.custom_bar = ttk.Frame(self.master)
        self.custom_bar.grid(row=0, column=0, sticky=("N", "S", "E", "W"))
        self.custom_bar.columnconfigure(3, weight=1)

        self.title_label = ttk.Label(self.custom_bar, text="Logowanie")
        self.title_label.grid(row=0, column=2, padx=5, sticky="W")

        self.exit_button = ttk.Button(
            self.custom_bar, text="X", command=main_window.master.destroy
        )
        self.exit_button.grid(row=0, column=4, padx=(0, 5), pady=3, sticky="E")

        ttk.Separator(self.master, orient="horizontal").grid(
            row=1, column=0, sticky=("W", "E")
        )

        self.content = ttk.Frame(self.master)
        self.content.grid(row=2, column=0, sticky=("N", "S", "E", "W"))

        self.user_name = ttk.Label(self.content, text="Nazwa:")
        self.user_password = ttk.Label(self.content, text="Hasło:")
        self.register_label = ttk.Label(
            self.content, text="Nie posiadasz jeszcze konta?"
        )

        self.user_name.grid(row=2, column=0, pady=4, padx=5, sticky="W")
        self.user_password.grid(row=3, column=0, pady=4, padx=5, sticky="W")
        self.register_label.grid(row=6, column=0, columnspan=2, pady=(4, 0), padx=5)

        self.user_name_input = ttk.Entry(self.content)
        self.user_password_input = ttk.Entry(self.content, show="*")

        self.user_name_input.grid(row=2, column=1, pady=(5, 5), padx=5)
        self.user_password_input.grid(row=3, column=1, pady=4, padx=5)

        self.remember_me = tk.StringVar()
        self.remember_me_button = ttk.Checkbutton(
            self.content,
            text="Zapamiętaj mnie",
            variable=self.remember_me,
            onvalue=True,
            offvalue=False,
        )
        self.remember_me_button.grid(row=4, columnspan=2, pady=4, padx=5, sticky="W")

        self.log_in_button = ttk.Button(
            self.content,
            text="Zaloguj",
            command=lambda: self.log_in(main_window, settings),
        )
        self.register_button = ttk.Button(
            self.content,
            text="Utwórz konto",
            command=lambda: self.register(settings=settings),
        )

        self.log_in_button.grid(row=5, columnspan=2, pady=4, padx=5, sticky=("W", "E"))
        self.register_button.grid(
            row=7, columnspan=2, pady=5, padx=5, sticky=("W", "E")
        )

        self.user_name_input.focus()
        self.user_password_input.bind(
            "<Return>", lambda _: self.log_in(main_window, settings)
        )
        self.custom_bar.bind(
            "<Button-1>", lambda event: get_pos(self, event, "custom_bar")
        )
        self.title_label.bind(
            "<Button-1>", lambda event: get_pos(self, event, "title_label")
        )

        center(self.master)

    def log_in(self, main_window, settings: dict, event=None):
        row = None
        with DataBaseConnection() as cursor:
            cursor.execute(
                "SELECT * FROM Konta_Plemiona WHERE UserName='"
                + self.user_name_input.get()
                + "' AND Password='"
                + self.user_password_input.get()
                + "'"
            )
            row = cursor.fetchone()
        if not row:
            custom_error(message="Wprowadzono nieprawidłowe dane", parent=self.master)
            return
        if not if_paid(str(row[5])):
            custom_error(message="Ważność konta wygasła", parent=self.master)
            return
        if row[6]:
            custom_error(message="Konto jest już obecnie w użyciu", parent=self.master)
            return
        email_address = main_window.entries_content["notifications"][
            "email_address"
        ].get()
        if not email_address or email_address == "0":
            print("smth")
            main_window.entries_content["notifications"]["email_address"].set(
                value=row[2]
            )
        main_window.verified_email = row[10]
        if not row[10]:
            main_window.verification_code = row[11]
        settings["account_expire_time"] = str(row[5])
        main_window.acc_expire_time.config(
            text=f'Konto ważne do {settings["account_expire_time"]}'
        )
        settings["logged"] = True

        if settings["logged"]:
            settings["user_name"] = self.user_name_input.get()
            if self.remember_me.get():
                settings["user_password"] = self.user_password_input.get()

            center(window=main_window.master, parent=self.master)
            self.master.destroy()
            main_window.master.deiconify()
            main_window.master.attributes("-alpha", 1.0)
            self.update_running_status(settings=settings, main_window=main_window)

    def register(self, settings: dict):
        # with DataBaseConnection() as cursor:
        #     # MAC address check
        #     MAC_Address = "-".join(
        #         [
        #             "{:02x}".format((uuid.getnode() >> ele) & 0xFF)
        #             for ele in range(0, 8 * 6, 8)
        #         ][::-1]
        #     )
        #     cursor.execute(
        #         "SELECT * FROM Konta_Plemiona WHERE AddressMAC='" + MAC_Address + "'"
        #     )
        #     db_answer = cursor.fetchone()
        #     if db_answer != None:
        #         custom_error("Utworzono już konto z tego komputera", parent=self.master)
        #         return
        #     else:
        #         self.master.withdraw()
        #         self.register_win = RegisterWindow(parent=self.master)
        self.master.withdraw()
        self.register_win = RegisterWindow(parent=self.master)

    def update_running_status(self, settings: dict, main_window):
        with DataBaseConnection() as cursor:
            cursor.execute(
                f"UPDATE Konta_Plemiona SET CurrentlyRunning=1"
                f"WHERE UserName='{settings['user_name']}'"
            )
        main_window.master.after(
            ms=595000,
            func=lambda: self.update_running_status(
                settings=settings, main_window=main_window
            ),
        )
