import re
import threading
import tkinter as tk
import uuid
from random import randint

import ttkbootstrap as ttk
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.validation import add_validation, validator

from database_connection import DataBaseConnection
from email_notifications import send_email
from gui_functions import center, custom_error, forget_row
from my_widgets import TopLevel


class RegisterWindow:
    def __init__(self, parent) -> None:
        self.master = TopLevel(title_text="Formularz rejestracyjny")

        # Change exit_button command
        def overwrite_button_command() -> None:
            center(window=parent, parent=self.master)
            self.master.destroy()
            parent.deiconify()

        self.master.exit_button.config(command=overwrite_button_command)

        self.content_frame = self.master.content_frame

        # Content
        ttk.Label(self.content_frame, text="Pola obowiązkowe").grid(
            row=0, column=0, columnspan=2, padx=5, pady=(5, 15), sticky="W"
        )
        ttk.Label(self.content_frame, text="Login:").grid(
            row=1, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        self.login = ttk.Entry(self.content_frame, width=25)
        self.login.grid(row=1, column=1, padx=(5, 5), pady=5, sticky=("E", "W"))

        self.login_status = tk.BooleanVar()

        @validator
        def login_validation(event=None):
            with DataBaseConnection() as cursor:
                cursor.execute(
                    "SELECT * FROM konta_plemiona WHERE user_name='"
                    + self.login.get()
                    + "'"
                )
                db_answer = cursor.fetchone()
                if not db_answer:
                    forget_row(widget_name=self.content_frame, row_number=2)
                    self.login_status.set(True)
                    return True
                else:
                    ttk.Label(
                        self.content_frame,
                        text="Podany login już istnieje",
                        bootstyle="danger",
                    ).grid(row=2, column=1, pady=(0, 5))
                    self.login_status.set(False)
                    return False

        add_validation(self.login, login_validation)

        ttk.Label(self.content_frame, text="Hasło:").grid(
            row=3, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        self.password = ttk.Entry(self.content_frame, show="*", width=25)
        self.password.grid(row=3, column=1, padx=(5, 5), pady=5, sticky=("E", "W"))

        ttk.Label(self.content_frame, text="Powtórz hasło:").grid(
            row=5, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        self.password_repeat = ttk.Entry(self.content_frame, show="*", width=25)
        self.password_repeat.grid(
            row=5, column=1, padx=(5, 5), pady=5, sticky=("E", "W")
        )

        self.password_status = tk.BooleanVar()

        @validator
        def password_validation(event=None):
            if self.password.get() == self.password_repeat.get():
                forget_row(self.content_frame, row_number=6)
                self.password.config(bootstyle="default")
                self.password_status.set(True)
                return True
            else:
                ttk.Label(
                    self.content_frame, text="Podano różne hasła", bootstyle="danger"
                ).grid(row=6, column=1, pady=(0, 5))
                self.password.config(bootstyle="danger")
                self.password.bind(
                    "<FocusIn>", lambda _: self.password.config(bootstyle="deafault")
                )
                self.password.bind(
                    "<FocusOut>", lambda _: self.password_repeat.validate()
                )
                self.password_status.set(False)
                return False

        add_validation(self.password_repeat, password_validation)

        ttk.Label(self.content_frame, text="Adres e-mail:").grid(
            row=7, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        self.email = ttk.Entry(self.content_frame, width=25)
        self.email.grid(row=7, column=1, padx=(5, 5), pady=5, sticky=("E", "W"))

        self.email_status = tk.BooleanVar()

        @validator
        def email_validation(event):
            if not re.search(pattern="@", string=self.email.get()):
                ttk.Label(
                    self.content_frame,
                    text="Podano nieprawidłowy adres",
                    bootstyle="danger",
                ).grid(row=8, column=1, pady=(0, 5))
                self.email_status.set(False)
                return False
            with DataBaseConnection() as cursor:
                cursor.execute(
                    "SELECT * FROM konta_plemiona WHERE email='"
                    + self.email.get()
                    + "'"
                )
                db_answer = cursor.fetchone()
                if db_answer:
                    ttk.Label(
                        self.content_frame,
                        text="Podany adres już istnieje",
                        bootstyle="danger",
                    ).grid(row=8, column=1, pady=(0, 5))
                    self.email_status.set(False)
                    return False
                else:
                    forget_row(self.content_frame, row_number=8)
                    self.email_status.set(True)
                    return True

        add_validation(self.email, email_validation)

        ttk.Label(self.content_frame, text="Powtórz e-mail:").grid(
            row=9, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        self.email_repeat = ttk.Entry(self.content_frame, width=25)
        self.email_repeat.grid(row=9, column=1, padx=(5, 5), pady=5, sticky=("E", "W"))

        self.email_repeat_status = tk.BooleanVar()

        @validator
        def email_repeat_validation(event):
            self.email.bind("<FocusOut>", lambda _: self.email_repeat.validate())
            if self.email.get() == self.email_repeat.get():
                forget_row(self.content_frame, row_number=10)
                self.email.config(bootstyle="default")
                self.email_repeat_status.set(True)
                return True
            else:
                ttk.Label(
                    self.content_frame,
                    text="Podano różne adresy e-mail",
                    bootstyle="danger",
                ).grid(row=10, column=1)
                self.email.config(bootstyle="danger")
                self.email.bind(
                    "<FocusIn>", lambda _: self.email.config(bootstyle="default")
                )
                self.email_repeat_status.set(False)
                return False

        add_validation(self.email_repeat, email_repeat_validation)

        ttk.Label(self.content_frame, text="Opcjonalne").grid(
            row=11, column=0, columnspan=2, padx=5, pady=15, sticky="W"
        )

        ttk.Label(self.content_frame, text="Login polecającego:").grid(
            row=12, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        self.recommended_by = ttk.Entry(self.content_frame, width=25)
        self.recommended_by.grid(
            row=12, column=1, padx=(5, 5), pady=5, sticky=("E", "W")
        )

        self.recomended_by_status = tk.BooleanVar(value=True)

        @validator
        def recomended_by_validation(event=None):
            with DataBaseConnection() as cursor:
                cursor.execute(
                    "SELECT * FROM konta_plemiona WHERE user_name='"
                    + self.recommended_by.get()
                    + "'"
                )
                db_answer = cursor.fetchone()
                if db_answer or not self.recommended_by.get():
                    forget_row(widget_name=self.content_frame, row_number=13)
                    self.recomended_by_status.set(True)
                    return True
                else:
                    ttk.Label(
                        self.content_frame,
                        text="Podany login nie istnieje",
                        bootstyle="danger",
                    ).grid(row=13, column=1)
                    self.recomended_by_status.set(False)
                    return False

        add_validation(self.recommended_by, recomended_by_validation)

        ToolTip(
            self.recommended_by,
            text="Pole opcjonalne:\n\nLogin konta używany do logowania się w bocie przez osobę polecającą.",
            topmost=True,
        )

        ttk.Button(
            self.content_frame,
            text="Utwórz konto",
            command=lambda: self.create_account(log_in_window=parent),
        ).grid(
            row=14,
            column=0,
            columnspan=2,
            padx=5,
            pady=(15, 5),
            sticky=("E", "W"),
        )

        center(self.master, parent=parent)
        self.master.attributes("-alpha", 1.0)

    def create_account(self, log_in_window) -> None:
        if (
            self.login_status.get()
            and self.password_status.get()
            and self.email_status.get()
            and self.email_repeat_status.get()
            and self.recomended_by_status.get()
        ):
            with DataBaseConnection() as cursor:
                # MAC address check
                MAC_Address = "-".join(
                    [
                        "{:02x}".format((uuid.getnode() >> ele) & 0xFF)
                        for ele in range(0, 8 * 6, 8)
                    ][::-1]
                )
                verification_code = randint(100000, 999999)
                cursor.execute(
                    f"""INSERT INTO konta_plemiona(
                            user_name,
                            password,
                            email,
                            address_mac,
                            currently_running,
                            invited_by,
                            verified_email,
                            verification_code,
                            captcha_solved) 
                        VALUES (
                            '{self.login.get()}',
                            '{self.password.get()}',
                            '{self.email.get()}',
                            '{MAC_Address}',
                            '0',
                            '{self.recommended_by.get()}',
                            '0',
                            '{verification_code}',
                            '0'
                    )"""
                )

            threading.Thread(
                target=send_email,
                kwargs={
                    "email_recepients": self.email.get(),
                    "email_subject": "Kod weryfikacyjny",
                    "email_body": f"Twój kod weryfikacyjny: {verification_code}",
                },
            ).start()
            center(window=log_in_window, parent=self.master)
            self.master.destroy()
            custom_error(
                message="Konto zostało pomyślnie utworzone!", parent=log_in_window
            )
            log_in_window.deiconify()
        else:
            custom_error(
                message="Uzupełnij prawidłowo obowiązkowe pola!", parent=self.master
            )
            return
