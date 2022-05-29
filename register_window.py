import re
import threading
import tkinter as tk
import uuid
import winreg
from contextlib import suppress
from random import randint

import geocoder
import ttkbootstrap as ttk
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.validation import add_validation, validator

from database_connection import DataBaseConnection
from email_notifications import send_email
from gui_functions import center, custom_error, forget_row, show_or_hide_password
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

        # Check if user has already created account using this current device
        exists = self.already_created(log_in_window=parent)

        self.content_frame = self.master.content_frame

        # Login
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
            if exists and self.login.get() == self.user_data["user_name"]:
                forget_row(widget_name=self.content_frame, row_number=2)
                self.login_status.set(True)
                return True
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

        # Password
        ttk.Label(self.content_frame, text="Hasło:").grid(
            row=3, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        self.password = ttk.Entry(self.content_frame, show="*", width=25)
        self.password.grid(row=3, column=1, padx=(5, 5), pady=5, sticky=tk.EW)
        self.show_image = ttk.PhotoImage(file="icons//view.png")
        self.hide_image = ttk.PhotoImage(file="icons//hide.png")
        self.password_button = ttk.Button(
            self.content_frame,
            image=self.hide_image,
            command=lambda: show_or_hide_password(
                parent=self, entry=self.password, button=self.password_button
            ),
            style="pure.TButton",
            takefocus=False,
        )
        self.password_button.grid(row=3, column=1, padx=(0, 12), sticky=ttk.E)
        # Password repeat
        ttk.Label(self.content_frame, text="Powtórz hasło:").grid(
            row=5, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        self.password_repeat = ttk.Entry(self.content_frame, show="*", width=25)
        self.password_repeat.grid(
            row=5, column=1, padx=(5, 5), pady=5, sticky=("E", "W")
        )
        # self.master.
        self.password_repeat_button = ttk.Button(
            self.content_frame,
            image=self.hide_image,
            command=lambda: show_or_hide_password(
                parent=self,
                entry=self.password_repeat,
                button=self.password_repeat_button,
            ),
            style="pure.TButton",
            takefocus=False,
        )
        self.password_repeat_button.grid(row=5, column=1, padx=(0, 12), sticky=ttk.E)

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

        # Email
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
            if exists and self.email.get() == self.user_data["email"]:
                forget_row(self.content_frame, row_number=8)
                self.email_status.set(True)
                return True
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

        # Email_repeat
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
        # Recommended_by
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
        tip_text = (
            "Pole opcjonalne:\n\n"
            "Login konta używany do logowania się w bocie przez osobę polecającą."
        )

        create_account = ttk.Button(
            self.content_frame,
            text="Utwórz konto",
            command=lambda: self.create_account(log_in_window=parent, exists=exists),
        )
        create_account.grid(
            row=14,
            column=0,
            columnspan=2,
            padx=5,
            pady=(15, 5),
            sticky=("E", "W"),
        )

        # Set fields if user already created his account
        if exists:
            self.login.insert(0, self.user_data["user_name"])
            self.password.insert(0, self.user_data["password"])
            self.password_repeat.insert(0, self.user_data["password"])
            self.email.insert(0, self.user_data["email"])
            self.email_repeat.insert(0, self.user_data["email"])
            if self.user_data["invited_by"]:
                self.recommended_by.insert(0, self.user_data["invited_by"])
                self.recommended_by.config(state="disabled")
                tip_text = "Pole zostało zablokowane."

            self.login_status.set(True)
            self.password_status.set(True)
            self.email_status.set(True)
            self.email_repeat_status.set(True)

            create_account.config(text="Aktualizuj konto")

        ToolTip(self.recommended_by, text=tip_text, topmost=True)

        center(self.master, parent=parent)
        self.master.attributes("-alpha", 1.0)

    def already_created(self, log_in_window) -> bool:
        """Check if user has already created account using this current device"""

        # try:
        #     key_reg = winreg.OpenKey(
        #         winreg.HKEY_CURRENT_USER, "Software\\TribalWarsBot\\AccountRegistered"
        #     )
        #     key_reg.Close()
        #     custom_error(
        #         message="Utworzono już konto z tego komputera\n"
        #         "Utworzenie nowego spowoduję jego nadpisanie nowymi danymi\n"
        #         "Z wyjątkiem daty ważności konta i loginu osoby polecającej",
        #         parent=self.master,
        #     )
        #     self.master.withdraw()
        #     self.register_win = RegisterWindow(parent=self.master)
        #     return
        # except OSError:
        #     pass

        self.mac_address = "-".join(
            [
                "{:02x}".format((uuid.getnode() >> ele) & 0xFF)
                for ele in range(0, 8 * 6, 8)
            ][::-1]
        )
        self.device_id = ""
        with suppress(FileNotFoundError), winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\SQMClient"
        ) as key:
            self.device_id = winreg.QueryValueEx(key, "MachineId")[0]

        with DataBaseConnection() as cursor:
            cursor.execute(
                "SELECT * FROM konta_plemiona WHERE address_mac='"
                + self.mac_address
                + "' or device_id='"
                + self.device_id
                + "'"
            )
            db_answer = cursor.fetchone()
            if db_answer != None:
                log_in_window.update()
                custom_error(
                    message="Utworzono już konto z tego komputera\n"
                    "Utworzenie nowego spowoduję jego nadpisanie nowymi danymi\n"
                    "Z wyjątkiem daty ważności konta i loginu osoby polecającej",
                    parent=log_in_window,
                )
                self.user_data = {
                    key[0]: value for key, value in zip(cursor.description, db_answer)
                }
                return True
            return False

    def create_account(self, log_in_window, exists: bool) -> None:
        if (
            self.login_status.get()
            and self.password_status.get()
            and self.email_status.get()
            and self.email_repeat_status.get()
            and self.recomended_by_status.get()
        ):

            verification_code = randint(100000, 999999)

            if exists:
                verified_email = 0
                if self.email.get() == self.user_data["email"]:
                    verified_email = self.user_data["verified_email"]
                    verification_code = self.user_data["verification_code"]
                invited_by = self.user_data["invited_by"]
                if self.user_data["invited_by"] != self.recommended_by.get():
                    invited_by = self.recommended_by.get()

                with DataBaseConnection() as cursor:
                    cursor.execute(
                        f"UPDATE Konta_Plemiona "
                        f"SET user_name='{self.login.get()}', "
                        f"password='{self.password.get()}', "
                        f"email='{self.email.get()}', "
                        f"address_mac='{self.mac_address}', "
                        f"device_id='{self.device_id}', "
                        f"currently_running=0, "
                        f"verified_email='{verified_email}', "
                        f"verification_code='{verification_code}', "
                        f"invited_by='{invited_by}' "
                        f"WHERE user_name='{self.user_data['user_name']}'"
                    )
                    if self.user_data["user_name"] != self.login.get():
                        cursor.execute(
                            f"UPDATE Konta_Plemiona "
                            f"SET invited_by = '{self.login.get()}' "
                            f"WHERE invited_by = '{self.user_data['user_name']}'"
                        )
            else:
                geolocation = geocoder.ip("me")
                country = geolocation.country
                city = geolocation.city
                with DataBaseConnection() as cursor:
                    cursor.execute(
                        f"""INSERT INTO konta_plemiona(
                                user_name,
                                password,
                                email,
                                address_mac,
                                device_id,
                                invited_by,
                                verification_code,
                                country,
                                city) 
                            VALUES (
                                '{self.login.get()}',
                                '{self.password.get()}',
                                '{self.email.get()}',
                                '{self.mac_address}',
                                '{self.device_id}',
                                '{self.recommended_by.get()}',
                                '{verification_code}',
                                '{country}',
                                '{city}'
                        )"""
                    )

            if not exists or self.email.get() != self.user_data["email"]:
                threading.Thread(
                    target=send_email,
                    kwargs={
                        "email_recepients": self.email.get(),
                        "email_subject": "Kod weryfikacyjny",
                        "email_body": f"Twój kod weryfikacyjny: {verification_code}",
                    },
                ).start()

            # Create key AccountRegistered in windows registry
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, "Software\\TribalWarsBot", 0, winreg.KEY_WRITE
            ) as key:
                winreg.SetValueEx(key, "AccountRegistered", 0, winreg.REG_NONE, None)

            center(window=log_in_window, parent=self.master)
            self.master.destroy()
            message = "Konto zostało pomyślnie utworzone!"
            if exists:
                message = "Konto zostało pomyślnie zaktualizowane!"
            custom_error(message=message, parent=log_in_window)
            log_in_window.deiconify()
        else:
            print(
                self.login_status.get(),
                self.password_status.get(),
                self.email_status.get(),
                self.email_repeat_status.get(),
                self.recomended_by_status.get(),
            )
            custom_error(
                message="Uzupełnij prawidłowo obowiązkowe pola!", parent=self.master
            )
            return
