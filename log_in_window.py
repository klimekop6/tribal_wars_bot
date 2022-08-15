import logging
import os
import threading
import tkinter as tk

import ttkbootstrap as ttk

from database_connection import DataBaseConnection
from gui_functions import (
    center,
    custom_error,
    delegate_things_to_other_thread,
    get_pos,
    invoke_checkbuttons,
    show_or_hide_password,
)
from register_window import RegisterWindow

# Logging module settings
logger = logging.getLogger(__name__)
if not os.path.exists("logs"):
    os.mkdir("logs")
f_handler = logging.FileHandler("logs/log.txt")
f_format = logging.Formatter(
    "\n%(levelname)s:%(name)s:%(asctime)s %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
)
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
logger.propagate = False


class LogInWindow:
    def __init__(self, main_window, settings: dict) -> None:
        settings["logged"] = False
        if "user_password" in settings:
            delegate_things_to_other_thread(settings=settings, main_window=main_window)
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
            else:
                if user_data["currently_running"]:
                    custom_error(message="Konto jest już obecnie w użyciu.")
                else:
                    main_window.user_data = user_data
                    self.after_correct_log_in(
                        main_window=main_window,
                        settings=settings,
                        user_data=user_data,
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
        self.user_name.grid(row=2, column=0, pady=4, padx=5, sticky="W")

        self.user_password = ttk.Label(self.content, text="Hasło:")
        self.user_password.grid(row=3, column=0, pady=4, padx=5, sticky="W")

        self.register_label = ttk.Label(
            self.content, text="Nie posiadasz jeszcze konta?"
        )
        self.register_label.grid(row=6, column=0, columnspan=2, pady=(4, 0), padx=5)

        self.user_name_input = ttk.Entry(self.content)
        self.user_name_input.grid(row=2, column=1, pady=(5, 5), padx=5)

        self.show_image = ttk.PhotoImage(file="icons//view.png")
        self.hide_image = ttk.PhotoImage(file="icons//hide.png")

        self.user_password_input = ttk.Entry(self.content, show="*")
        self.user_password_input.grid(row=3, column=1, pady=4, padx=5)
        self.show_or_hide_password = ttk.Button(
            self.content,
            image=self.hide_image,
            command=lambda: show_or_hide_password(
                parent=self,
                entry=self.user_password_input,
                button=self.show_or_hide_password,
            ),
            style="pure.TButton",
            takefocus=False,
        )
        self.show_or_hide_password.grid(row=3, column=1, padx=(0, 12), sticky="E")

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
            command=lambda: self.register(),
        )

        self.log_in_button.grid(row=5, columnspan=2, pady=4, padx=5, sticky=("W", "E"))
        self.register_button.grid(
            row=7, columnspan=2, pady=5, padx=5, sticky=("W", "E")
        )

        self.user_name_input.focus_force()
        self.user_password_input.bind(
            "<Return>",
            lambda _: self.log_in(main_window, settings),
        )
        self.custom_bar.bind(
            "<Button-1>", lambda event: get_pos(self, event, "custom_bar")
        )
        self.title_label.bind(
            "<Button-1>", lambda event: get_pos(self, event, "title_label")
        )

        center(self.master)

    def after_correct_log_in(
        self,
        main_window,
        settings: dict,
        user_data: dict,
        parent=None,
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

        # Remove from grid some widgets for users without privilages
        if user_data["user_name"] not in ("klimekop6", "klimek123"):
            main_window.mine_coin_frame.grid_remove()

        invoke_checkbuttons(parent=main_window.master)
        center(main_window.master, parent=parent)
        main_window.master.deiconify()
        main_window.master.attributes("-alpha", 1.0)
        main_window.master.attributes("-topmost", 1)
        main_window.master.focus_force()
        self.update_db_running_status(main_window=main_window)

    def log_in(self, main_window, settings: dict):
        delegate_things_to_other_thread(settings=settings, main_window=main_window)
        db_answer = None
        user_data = None
        with DataBaseConnection() as cursor:
            if not cursor:
                return
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
        if user_data["currently_running"]:
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

    def register(self):
        self.master.withdraw()
        try:
            self.register_win = RegisterWindow(parent=self.master)
        except:
            logger.error("RegisterWindow exception", exc_info=True)
            custom_error(
                message="Wystąpił nieoczekiwany błąd.\nInformację o błędzie zapisane zostały "
                "w pliku log.txt. Plik znajduję się w podfolderze, o nazwie logs, w głównym folderze aplikacji TribalWarsBot. "
                "W celu uzyskania pomocy prześlij wspomniany plik na adres k.spec@tuta.io",
                parent=self.master,
                sticky=ttk.W,
            )
            self.master.deiconify()

    def update_db_running_status(self, main_window):
        """Inform database about account activity every 10min"""

        def data_update(main_window) -> None:
            captcha_counter = main_window.captcha_counter.get()
            if captcha_counter > 0:
                sql_str = (
                    f"UPDATE konta_plemiona "
                    f"SET currently_running=1, captcha_solved=captcha_solved + {captcha_counter} "
                    f"WHERE user_name='{main_window.user_data['user_name']}'"
                )
                main_window.captcha_counter.set(0)
            else:
                sql_str = (
                    f"UPDATE konta_plemiona SET currently_running=1 "
                    f"WHERE user_name='{main_window.user_data['user_name']}'"
                )

            with DataBaseConnection(ignore_erros=True) as cursor:
                cursor.execute(sql_str)

        threading.Thread(
            target=lambda: data_update(main_window=main_window),
            name="status_running_update",
            daemon=True,
        ).start()

        main_window.master.after(
            ms=595_000,
            func=lambda: self.update_db_running_status(main_window=main_window),
        )
