import re
import threading
import tkinter as tk
import uuid
import winreg
from contextlib import suppress
from random import randint

import geocoder
import ttkbootstrap as ttk
from ttkbootstrap import localization
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.validation import add_validation, validator

from app.notifications.email import send_email
from app.tribal_wars_bot_api import TribalWarsBotApi
from gui.functions import center, custom_error, forget_row, show_or_hide_password
from gui.widgets.my_widgets import TopLevel

translate = localization.MessageCatalog.translate


class RegisterWindow:
    def __init__(self, parent) -> None:
        self.master = TopLevel(title_text=translate("Registration form"))

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
        ttk.Label(self.content_frame, text=translate("Required fields")).grid(
            row=0, column=0, columnspan=2, padx=5, pady=(5, 15), sticky="W"
        )
        ttk.Label(self.content_frame, text=translate("Username:")).grid(
            row=1, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        self.login = ttk.Entry(self.content_frame, width=25)
        self.login.grid(row=1, column=1, padx=(5, 5), pady=5, sticky=("E", "W"))

        self.login_status = tk.BooleanVar()

        @validator
        def login_validation(event=None):
            def on_error(msg: str) -> None:
                ttk.Label(
                    self.content_frame,
                    text=msg,
                    bootstyle="danger",
                ).grid(row=2, column=1, pady=(0, 5))
                self.login_status.set(False)
                return False

            if exists and self.login.get() == self.user_data["user_name"]:
                forget_row(parent=self.content_frame, row_number=2)
                self.login_status.set(True)
                return True
            # API GET /register DONE
            response = TribalWarsBotApi(f"/register?user_name={self.login.get()}").get()
            if not response.ok:
                return on_error(translate("Database error occurred"))
            if response.json()["no_exist"]:
                forget_row(parent=self.content_frame, row_number=2)
                self.login_status.set(True)
                return True
            else:
                return on_error(translate("Given login is already in use"))

        add_validation(self.login, login_validation)

        # Password
        ttk.Label(self.content_frame, text=translate("Password:")).grid(
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
        ttk.Label(self.content_frame, text=translate("Repeat password:")).grid(
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
                    self.content_frame,
                    text=translate("Passwords must be the same"),
                    bootstyle="danger",
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
        ttk.Label(self.content_frame, text=translate("Email address:")).grid(
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
                    text=translate("Invalid email address"),
                    bootstyle="danger",
                ).grid(row=8, column=1, pady=(0, 5))
                self.email_status.set(False)
                return False
            if exists and self.email.get() == self.user_data["email"]:
                forget_row(self.content_frame, row_number=8)
                self.email_status.set(True)
                return True

            def on_error(msg: str) -> None:
                ttk.Label(
                    self.content_frame,
                    text=msg,
                    bootstyle="danger",
                ).grid(row=8, column=1, pady=(0, 5))
                self.email_status.set(False)
                return False

            # API GET /register DONE
            response = TribalWarsBotApi(f"/register?email={self.email.get()}").get()
            if not response.ok:
                return on_error(translate("Database error occurred"))
            if response.json()["no_exist"]:
                forget_row(self.content_frame, row_number=8)
                self.email_status.set(True)
                return True
            else:
                return on_error(translate("That address is already in use"))

        add_validation(self.email, email_validation)

        # Email_repeat
        ttk.Label(self.content_frame, text=translate("Repeat email:")).grid(
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
                    text=translate("Emails must be the same"),
                    bootstyle="danger",
                ).grid(row=10, column=1)
                self.email.config(bootstyle="danger")
                self.email.bind(
                    "<FocusIn>", lambda _: self.email.config(bootstyle="default")
                )
                self.email_repeat_status.set(False)
                return False

        add_validation(self.email_repeat, email_repeat_validation)

        ttk.Label(self.content_frame, text=translate("Not required")).grid(
            row=11, column=0, columnspan=2, padx=5, pady=15, sticky="W"
        )
        # Recommended_by
        ttk.Label(self.content_frame, text=translate("Referrer Login:")).grid(
            row=12, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        self.recommended_by = ttk.Entry(self.content_frame, width=25)
        self.recommended_by.grid(
            row=12, column=1, padx=(5, 5), pady=5, sticky=("E", "W")
        )

        self.recomended_by_status = tk.BooleanVar(value=True)

        @validator
        def recomended_by_validation(event=None):
            def on_error(msg: str) -> None:
                ttk.Label(
                    self.content_frame,
                    text=msg,
                    bootstyle="danger",
                ).grid(row=13, column=1)
                self.recomended_by_status.set(False)
                return False

            # API GET /register DONE
            response = TribalWarsBotApi(
                f"/register?user_name={self.recommended_by.get()}"
            ).get()
            if not response.ok:
                return on_error(translate("Database error occurred"))
            if self.recommended_by.get() == self.login.get():
                return on_error(translate("Prohibited activity"))
            if not response.json()["no_exist"] or not self.recommended_by.get():
                forget_row(parent=self.content_frame, row_number=13)
                self.recomended_by_status.set(True)
                return True
            else:
                return on_error(translate("Given login does not exist"))

        add_validation(self.recommended_by, recomended_by_validation)
        tip_text = translate(
            "Not required:\n\n"
            "The account login used to log in to the bot by the referrer."
        )

        create_account = ttk.Button(
            self.content_frame,
            text=translate("Create account"),
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
                tip_text = translate("The field has been blocked.")

            self.login_status.set(True)
            self.password_status.set(True)
            self.email_status.set(True)
            self.email_repeat_status.set(True)

            create_account.config(text=translate("Update account"))

        ToolTip(self.recommended_by, text=tip_text, topmost=True)

        center(self.master, parent=parent)
        self.master.attributes("-alpha", 1.0)

    def already_created(self, log_in_window) -> bool:
        """Check if user has already created account using this current device"""

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
        # API GET /register DONE
        response = TribalWarsBotApi(
            f"/register?address_mac={self.mac_address}&device_id={self.device_id}&operator=or"
        ).get()
        if not response.ok:
            custom_error(
                message=translate(
                    "Database is currently unavailable, pls try again later"
                ),
                parent=log_in_window,
            )
            return False
        if not response.json()["no_exist"]:
            log_in_window.update()
            custom_error(
                message=translate(
                    "An account has already been created from this computer\n"
                    "Creating a new one will cause it to be overwritten with new data\n"
                    "Except for the expiration date of the account and the login of the referrer"
                ),
                parent=log_in_window,
            )
            response = TribalWarsBotApi(
                f"/user?address_mac={self.mac_address}&device_id={self.device_id}&operator=or"
            ).get()
            if not response.ok:
                custom_error(
                    message=translate(
                        "Database is currently unavailable, pls try again later"
                    ),
                    parent=log_in_window,
                )
                return False
            self.user_data = response.json()
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
                # API PATCH /user/<user_name> DONE
                data = {
                    "user_name": self.login.get(),
                    "password": self.password.get(),
                    "email": self.email.get(),
                    "address_mac": self.mac_address,
                    "device_id": self.device_id,
                    "verified_email": verified_email,
                    "verification_code": verification_code,
                    "invited_by": invited_by,
                }
                TribalWarsBotApi(
                    f"/user?user_name={self.user_data['user_name']}", json=data
                ).patch(sync=False)
                if self.user_data["user_name"] != self.login.get():
                    data = {"invited_by": self.login.get()}
                    TribalWarsBotApi(
                        f"/user?invited_by={self.user_data['user_name']}", json=data
                    ).patch(sync=False)
            else:
                geolocation = geocoder.ip("me")
                country = geolocation.country
                city = geolocation.city
                # API POST /register DONE
                data = {
                    "user_name": self.login.get(),
                    "password": self.password.get(),
                    "email": self.email.get(),
                    "address_mac": self.mac_address,
                    "device_id": self.device_id,
                    "invited_by": self.recommended_by.get(),
                    "verification_code": verification_code,
                    "country": country,
                    "city": city,
                }
                TribalWarsBotApi("/register", json=data).post(sync=False)

            if not exists or self.email.get() != self.user_data["email"]:
                threading.Thread(
                    target=send_email,
                    kwargs={
                        "email_recepients": self.email.get(),
                        "email_subject": translate("Verification code"),
                        "email_body": f"{translate('Your verification code:')} {verification_code}",
                    },
                ).start()

            # Create key AccountRegistered in windows registry
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, "Software\\TribalWarsBot", 0, winreg.KEY_WRITE
            ) as key:
                winreg.SetValueEx(key, "AccountRegistered", 0, winreg.REG_NONE, None)

            center(window=log_in_window, parent=self.master)
            self.master.destroy()
            message = translate("Account has been successfully created!")
            if exists:
                message = translate("Account has been successfully updated!")
            custom_error(message=message, parent=log_in_window)
            log_in_window.deiconify()
        else:
            custom_error(
                message=translate("Fill in the required fields correctly!"),
                parent=self.master,
            )
            return
