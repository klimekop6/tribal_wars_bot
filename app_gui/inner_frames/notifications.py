from functools import partial
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap import localization
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.validation import add_validation

from gui_functions import is_int
from my_widgets import ScrollableFrame

if TYPE_CHECKING:
    from app_gui.windows.main_window import MainWindow

translate = localization.MessageCatalog.translate


class Notifications(ScrollableFrame):
    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ) -> None:

        super().__init__(parent)
        self.columnconfigure((0, 1), weight=1)

        self.invalid = 0
        add_int_validation = partial(
            add_validation,
            func=is_int,
            navi_button=main_window.navigation.notifications,
            parent=self,
        )

        entries_content["notifications"] = {}
        notifications = entries_content["notifications"]

        ttk.Label(self, text=translate("Attack labels")).grid(
            row=0, column=0, padx=10, pady=(0, 20), sticky="W"
        )

        notifications["check_incoming_attacks"] = ttk.BooleanVar()

        def change_entry(value, widget) -> None:
            if value.get():
                widget.config(state="normal")
            else:
                widget.config(state="disabled")

        def check_incoming_attacks():
            change_entry(
                value=notifications["check_incoming_attacks"],
                widget=self.check_incoming_attacks_sleep_time,
            )
            if main_window.loading:
                return
            if not notifications["check_incoming_attacks"].get():
                if notifications["email_notifications"].get():
                    self.email_notifications.invoke()
                if notifications["sms_notifications"].get():
                    self.sms_notifications.invoke()
                if notifications["sound_notifications"].get():
                    self.sound_notifications.invoke()

        self.check_incoming_attacks = ttk.Checkbutton(
            self,
            text=translate("Check incoming attacks"),
            variable=notifications["check_incoming_attacks"],
            onvalue=True,
            offvalue=False,
            command=check_incoming_attacks,
        )
        self.check_incoming_attacks.grid(
            row=7, column=0, columnspan=2, padx=(30, 5), pady=(0, 10), sticky="W"
        )

        self.check_incoming_attacks_label = ttk.Label(
            self, text=translate("Create attack labels every \[min]")
        )
        self.check_incoming_attacks_label.grid(
            row=8, column=0, padx=(30, 5), pady=5, sticky="W"
        )

        notifications["check_incoming_attacks_sleep_time"] = ttk.IntVar()
        self.check_incoming_attacks_sleep_time = ttk.Entry(
            self,
            textvariable=notifications["check_incoming_attacks_sleep_time"],
            width=5,
            justify="center",
        )
        self.check_incoming_attacks_sleep_time.grid(
            row=8, column=1, padx=(5, 30), pady=5, sticky="E"
        )
        add_int_validation(self.check_incoming_attacks_sleep_time, default=30, min=1)

        ttk.Label(self, text=translate("Notifications")).grid(
            row=9, column=0, padx=10, pady=(20, 10), sticky="W"
        )

        notifications["email_notifications"] = ttk.BooleanVar()

        def email_notifications():
            change_entry(
                value=notifications["email_notifications"],
                widget=self.email_notifications_entry,
            )
            if main_window.loading:
                return
            if (
                notifications["email_notifications"].get()
                and not notifications["check_incoming_attacks"].get()
            ):
                self.check_incoming_attacks.invoke()

        self.email_notifications = ttk.Checkbutton(
            self,
            text=translate("Email notifications about incoming noblemans"),
            variable=notifications["email_notifications"],
            onvalue=True,
            offvalue=False,
            command=email_notifications,
        )
        self.email_notifications.grid(
            row=10, column=0, columnspan=2, padx=(30, 5), pady=10, sticky="W"
        )

        ttk.Label(self, text=translate("Send notifications to email address:")).grid(
            row=11, column=0, padx=(30, 5), pady=10, sticky="W"
        )
        notifications["email_address"] = ttk.StringVar()
        self.email_notifications_entry = ttk.Entry(
            self,
            textvariable=notifications["email_address"],
            justify="center",
        )
        self.email_notifications_entry.grid(
            row=11, column=1, padx=(5, 30), pady=10, sticky="E"
        )

        notifications["sms_notifications"] = ttk.BooleanVar()

        def sms_notifications():
            change_entry(
                value=notifications["sms_notifications"],
                widget=self.sms_notifications_entry,
            )
            if main_window.loading:
                return
            if (
                notifications["sms_notifications"].get()
                and not notifications["check_incoming_attacks"].get()
            ):
                self.check_incoming_attacks.invoke()

        self.sms_notifications = ttk.Checkbutton(
            self,
            text=translate("Sms notifications about incoming noblemans"),
            variable=notifications["sms_notifications"],
            onvalue=True,
            offvalue=False,
            command=sms_notifications,
        )
        self.sms_notifications.grid(
            row=12, column=0, columnspan=2, padx=(30, 5), pady=10, sticky="W"
        )

        ttk.Label(self, text=translate("Send notifications to phone number:")).grid(
            row=13, column=0, padx=(30, 5), pady=10, sticky="W"
        )
        notifications["phone_number"] = ttk.StringVar()

        self.sms_notifications_entry = ttk.Entry(
            self,
            textvariable=notifications["phone_number"],
            justify="center",
        )
        self.sms_notifications_entry.grid(
            row=13, column=1, padx=(5, 30), pady=10, sticky="E"
        )

        ToolTip(
            self.sms_notifications_entry,
            text=(
                "Dostępne są tylko polskie 9 cyfrowe numery.\n\n"
                "Przykładowy numer: 739162666"
            ),
            topmost=True,
        )

        notifications["sound_notifications"] = ttk.BooleanVar()

        def sound_notifications():
            if main_window.loading:
                return
            if (
                notifications["sound_notifications"].get()
                and not notifications["check_incoming_attacks"].get()
            ):
                self.check_incoming_attacks.invoke()

        self.sound_notifications = ttk.Checkbutton(
            self,
            text=translate("Sound notifications about incoming noblemans"),
            variable=notifications["sound_notifications"],
            onvalue=True,
            offvalue=False,
            command=sound_notifications,
        )
        self.sound_notifications.grid(
            row=14, column=0, columnspan=2, padx=(30, 5), pady=10, sticky="W"
        )
