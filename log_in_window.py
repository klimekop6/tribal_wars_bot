import tkinter as tk
import uuid

import ttkbootstrap as ttk

from database_connection import DataBaseConnection
from gui_functions import center, custom_error, get_pos, invoke_checkbuttons
from register_window import RegisterWindow


class LogInWindow:
    def __init__(self, main_window, settings: dict) -> None:
        settings["logged"] = False
        if "user_password" in settings:
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
                        key[0]: value
                        for key, value in zip(cursor.description, db_answer)
                    }
            if not db_answer:
                custom_error(message="Automatyczne logowanie nie powiodło się.")
            # elif not if_paid(str(db_answer[5])):
            #     custom_error(message="Ważność konta wygasła.")
            elif db_answer[6]:
                custom_error(message="Konto jest już obecnie w użyciu.")
            else:
                main_window.user_data = user_data
                self.after_correct_log_in(
                    main_window=main_window, settings=settings, user_data=user_data
                )
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

    def after_correct_log_in(
        self, main_window, settings: dict, user_data: dict, parent=None
    ) -> None:
        settings["logged"] = True

        email_address = main_window.entries_content["notifications"][
            "email_address"
        ].get()
        if not email_address or email_address == "0":
            main_window.entries_content["notifications"]["email_address"].set(
                user_data["email"]
            )
        main_window.verified_email = user_data["verified_email"]
        if not user_data["verified_email"]:
            main_window.verified_email_label.config(
                text="Zweryfikowany adres e-mail: Nie"
            )
        else:
            main_window.verified_email_label.config(
                text="Zweryfikowany adres e-mail: Tak"
            )

        settings["account_expire_time"] = str(user_data["active_until"])
        main_window.acc_expire_time.config(
            text=f'Konto ważne do {user_data["active_until"]}'
        )

        invoke_checkbuttons(parent=main_window.master)
        center(main_window.master, parent=parent)
        main_window.master.deiconify()
        main_window.master.attributes("-alpha", 1.0)
        self.update_db_running_status(settings=settings, main_window=main_window)

    def log_in(self, main_window, settings: dict, event=None):
        db_answer = None
        user_data = None
        with DataBaseConnection() as cursor:
            cursor.execute(
                "SELECT * FROM konta_plemiona WHERE user_name='"
                + self.user_name_input.get()
                + "' AND password='"
                + self.user_password_input.get()
                + "'"
            )
            db_answer = cursor.fetchone()
            if db_answer:
                user_data = {
                    key[0]: value for key, value in zip(cursor.description, db_answer)
                }
        if not db_answer:
            custom_error(message="Wprowadzono nieprawidłowe dane", parent=self.master)
            return
        # if not if_paid(str(db_answer[5])):
        #     custom_error(message="Ważność konta wygasła", parent=self.master)
        #     return
        if db_answer[6]:
            custom_error(message="Konto jest już obecnie w użyciu", parent=self.master)
            return

        settings["user_name"] = self.user_name_input.get()
        if self.remember_me.get():
            settings["user_password"] = self.user_password_input.get()

        main_window.user_data = user_data

        self.master.attributes("-alpha", 1.0)
        self.after_correct_log_in(
            main_window=main_window,
            settings=settings,
            user_data=user_data,
            parent=self.master,
        )
        self.master.destroy()

    def register(self, settings: dict):
        with DataBaseConnection() as cursor:
            # MAC address check
            MAC_Address = "-".join(
                [
                    "{:02x}".format((uuid.getnode() >> ele) & 0xFF)
                    for ele in range(0, 8 * 6, 8)
                ][::-1]
            )
            cursor.execute(
                "SELECT * FROM konta_plemiona WHERE address_mac='" + MAC_Address + "'"
            )
            db_answer = cursor.fetchone()
            if db_answer != None:
                custom_error("Utworzono już konto z tego komputera", parent=self.master)
                return
            else:
                self.master.withdraw()
                self.register_win = RegisterWindow(parent=self.master)
        # self.master.withdraw()
        # self.register_win = RegisterWindow(parent=self.master)

    def update_db_running_status(self, settings: dict, main_window):
        """Inform database about account activity every 10min"""

        with DataBaseConnection() as cursor:
            cursor.execute(
                f"UPDATE konta_plemiona SET currently_running=1"
                f"WHERE user_name='{settings['user_name']}'"
            )
        main_window.master.after(
            ms=595000,
            func=lambda: self.update_db_running_status(
                settings=settings, main_window=main_window
            ),
        )
