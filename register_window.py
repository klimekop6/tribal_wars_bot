import tkinter as tk

import ttkbootstrap as ttk
from click import command

from database_connection import DataBaseConnection
from gui_functions import center
from my_widgets import TopLevel


class RegisterWindow:
    def __init__(self, parent) -> None:
        self.master = TopLevel(title_text="Formularz rejestracyjny")
        # self.master = tk.Toplevel(borderwidth=1, relief="groove")
        # self.master.geometry("500x750")

        # content_frame = tk.Frame(self.master)
        # content_frame.grid(row=0, column=0)

        self.content_frame = self.master.content_frame

        # Content
        self.login = tk.StringVar()
        ttk.Label(self.content_frame, text="Login:").grid(
            row=0, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        ttk.Entry(self.content_frame, textvariable=self.login, width=25).grid(
            row=0, column=1, padx=(5, 5), pady=5, sticky=("E", "W")
        )

        self.password = tk.StringVar()
        ttk.Label(self.content_frame, text="Hasło:").grid(
            row=2, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        ttk.Entry(
            self.content_frame, textvariable=self.password, show="*", width=25
        ).grid(row=2, column=1, padx=(5, 5), pady=5, sticky=("E", "W"))

        self.password_repeat = tk.StringVar()
        ttk.Label(self.content_frame, text="Powtórz hasło:").grid(
            row=3, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        ttk.Entry(
            self.content_frame, textvariable=self.password_repeat, show="*", width=25
        ).grid(row=3, column=1, padx=(5, 5), pady=5, sticky=("E", "W"))

        self.email = tk.StringVar()
        ttk.Label(self.content_frame, text="Adres e-mail:").grid(
            row=4, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        ttk.Entry(self.content_frame, textvariable=self.email, width=25).grid(
            row=4, column=1, padx=(5, 5), pady=5, sticky=("E", "W")
        )

        self.email_repeat = tk.StringVar()
        ttk.Label(self.content_frame, text="Powtórz e-mail:").grid(
            row=5, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        ttk.Entry(self.content_frame, textvariable=self.email_repeat, width=25).grid(
            row=5, column=1, padx=(5, 5), pady=5, sticky=("E", "W")
        )

        self.recommended_by = tk.StringVar()
        ttk.Label(self.content_frame, text="Login polecającego:").grid(
            row=6, column=0, padx=(5, 5), pady=5, sticky="W"
        )
        ttk.Entry(self.content_frame, textvariable=self.recommended_by, width=25).grid(
            row=6, column=1, padx=(5, 5), pady=5, sticky=("E", "W")
        )

        ttk.Button(
            self.content_frame,
            text="Utwórz konto",
            command=lambda: self.create_account(log_in_window=parent),
        ).grid(
            row=8,
            column=0,
            columnspan=2,
            padx=5,
            pady=5,
            sticky=("E", "W"),
        )

        center(self.master)
        self.master.attributes("-alpha", 1.0)

    def create_account(self, log_in_window) -> None:
        self.master.destroy()
        log_in_window.deiconify()
