import os
import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap import localization

translate = localization.MessageCatalog.translate

from typing import TYPE_CHECKING

from app.functions import (
    delegate_things_to_other_thread,
    expiration_warning,
    first_app_login,
)
from app.logging import add_event_handler, get_logger
from app.tribal_wars_bot_api import TribalWarsBotApi
from gui.functions import (
    center,
    custom_error,
    get_pos,
    invoke_checkbuttons,
    show_or_hide_password,
)

from .register import RegisterWindow

if TYPE_CHECKING:
    from gui.windows.main import MainWindow

# Logging module settings
if not os.path.exists("logs"):
    os.mkdir("logs")
logger = get_logger(__name__)


class LogInWindow:
    def __init__(self, main_window: "MainWindow", settings: dict) -> None:
        settings["logged"] = False
        if "user_password" in settings:
            delegate_things_to_other_thread(settings=settings, main_window=main_window)
            # API POST /login DONE
            data = {
                "user_name": settings["user_name"],
                "user_password": settings["user_password"],
            }
            response = TribalWarsBotApi("/login", json=data).post()
            if response is False:
                custom_error(
                    message=translate(
                        "Database is currently unavailable, pls try again later"
                    )
                )
            elif not response.ok:
                custom_error(message=translate("Auto login failed"))
            else:
                user_data = response.json()
                if user_data["currently_running"]:
                    custom_error(message=translate("The account is already in use"))
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

        self.title_label = ttk.Label(self.custom_bar, text=translate("Log-in window"))
        self.title_label.grid(row=0, column=2, padx=5, sticky="W")

        self.exit_button = ttk.Button(
            self.custom_bar, text="X", command=main_window.hidden_root.destroy
        )
        self.exit_button.grid(row=0, column=4, padx=(0, 5), pady=3, sticky="E")

        ttk.Separator(self.master, orient="horizontal").grid(
            row=1, column=0, sticky=("W", "E")
        )

        self.content = ttk.Frame(self.master)
        self.content.grid(row=2, column=0, sticky=("N", "S", "E", "W"))

        self.user_name = ttk.Label(self.content, text=translate("Username:"))
        self.user_name.grid(row=2, column=0, pady=4, padx=5, sticky="W")

        self.user_password = ttk.Label(self.content, text=translate("Password:"))
        self.user_password.grid(row=3, column=0, pady=4, padx=5, sticky="W")

        self.register_label = ttk.Label(
            self.content, text=translate("Don't have an account yet?")
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
            text=translate("Remember me"),
            variable=self.remember_me,
            onvalue=True,
            offvalue=False,
        )
        self.remember_me_button.grid(row=4, columnspan=2, pady=4, padx=5, sticky="W")

        self.log_in_button = ttk.Button(
            self.content,
            text=translate("Log in"),
            command=lambda: self.log_in(main_window, settings),
        )
        self.register_button = ttk.Button(
            self.content,
            text=translate("Create account"),
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
        main_window: "MainWindow",
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
            main_window.control_panel.verified_email_label.config(
                text=translate("Verified address e-mail: No")
            )
        else:
            main_window.control_panel.verified_email_label.config(
                text=translate("Verified address e-mail: Yes")
            )

        settings["account_expire_time"] = str(user_data["active_until"])
        main_window.control_panel.acc_expire_time.config(
            text=f'{translate("Account expiration time")} {user_data["active_until"]}'
        )

        invoke_checkbuttons(parent=main_window.master, main_window=main_window)
        main_window.master.deiconify()
        main_window.master.attributes("-topmost", 1)
        main_window.hidden_root.focus()
        add_event_handler(settings=settings)
        self.update_db_running_status(main_window=main_window)
        main_window.master.update()
        center(main_window.master, parent=parent)
        if settings["first_lunch"]:
            first_app_login(settings=settings, main_window=main_window)
        expiration_warning(settings=settings, main_window=main_window)
        main_window.master.update_idletasks()
        main_window.master.attributes("-alpha", 1.0)

    def log_in(self, main_window: "MainWindow", settings: dict):
        delegate_things_to_other_thread(settings=settings, main_window=main_window)
        # API POST /login DONE
        data = {
            "user_name": self.user_name_input.get(),
            "user_password": self.user_password_input.get(),
        }
        response = TribalWarsBotApi("/login", json=data).post()
        if response is False:
            custom_error(
                message=translate(
                    "Database is currently unavailable, pls try again later"
                ),
                parent=self.master,
            )
            return
        if not response.ok:
            custom_error(
                message=translate("Incorrect data entered"), parent=self.master
            )
            return
        user_data = response.json()
        if user_data["currently_running"]:
            custom_error(
                message=translate("The account is already in use"), parent=self.master
            )
            return
        settings["user_name"] = self.user_name_input.get()
        if self.remember_me.get():
            settings["user_password"] = self.user_password_input.get()

        main_window.user_data = user_data

        self.master.attributes("-alpha", 0.0)
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
            logger.error("RegisterWindow exception")
            custom_error(
                message="Wystąpił nieoczekiwany błąd.\nInformację o błędzie zapisane zostały "
                "w pliku log.txt. Plik znajduję się w podfolderze, o nazwie logs, w głównym folderze aplikacji TribalWarsBot. "
                "W celu uzyskania pomocy prześlij wspomniany plik na adres k.spec@tuta.io",
                parent=self.master,
                sticky=ttk.W,
            )
            self.master.deiconify()

    def update_db_running_status(self, main_window: "MainWindow"):
        """Inform database about account activity every 10min"""

        # API PATCH /status DONE
        captcha_counter = main_window.captcha_counter.get()
        user_name = main_window.user_data["user_name"]
        data = {"currently_running": 1, "user_name": user_name}
        if captcha_counter > 0:
            data["captcha_solved"] = captcha_counter
            main_window.captcha_counter.set(0)
        TribalWarsBotApi("/status", json=data).patch(sync=False)

        main_window.master.after(
            ms=595_000,
            func=lambda: self.update_db_running_status(main_window=main_window),
        )
