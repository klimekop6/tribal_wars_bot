import threading
import tkinter as tk
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap import localization
from ttkbootstrap.tooltip import ToolTip

from gui.functions import custom_error
from gui.widgets.my_widgets import ScrollableFrame
from gui.windows.new_world import add_new_world
from gui.windows.payment import PaymentWindow

if TYPE_CHECKING:
    from gui.windows.main import MainWindow

translate = localization.MessageCatalog.translate


class Settings(ScrollableFrame):
    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ) -> None:

        super().__init__(parent, max_height=True)
        self.columnconfigure((0, 1), weight=1)

        self.rowconfigure(5, weight=1)

        self.entries_content = entries_content

        ttk.Label(self, text=translate("Choose server and world number")).grid(
            row=0, column=0, padx=(15, 0), pady=10, sticky="W"
        )

        entries_content["game_url"] = ttk.StringVar()
        self.game_url = ttk.Combobox(
            self,
            textvariable=entries_content["game_url"],
            state="readonly",
            justify="center",
            width=20,
        )
        self.game_url.grid(row=0, column=1, padx=10, pady=10)
        self.game_url.set(translate("Choose server"))
        self.game_url["values"] = [
            "plemiona.pl",
            "die-staemme.de",
            "tribalwars.net",
            "tribalwars.nl",
            "tribalwars.se",
            "tribalwars.com.br",
            "tribalwars.com.pt",
            "divokekmeny.cz",
            "staemme.ch",
            "triburile.ro",
            "voyna-plemyon.ru",
            "fyletikesmaxes.gr",
            "no.tribalwars.com",
            "divoke-kmene.sk",
            "klanhaboru.hu",
            "tribalwars.dk",
            "tribals.it",
            "klanlar.org",
            "guerretribale.fr",
            "guerrastribales.es",
            "tribalwars.ae",
            "tribalwars.co.uk",
            "vojnaplemen.si",
            "plemena.com",
            "tribalwars.asia",
            "tribalwars.us",
        ]

        entries_content["world_number"] = ttk.StringVar()
        self.world_number_input = ttk.Entry(
            self,
            textvariable=entries_content["world_number"],
            width=5,
            justify="center",
        )
        self.world_number_input.grid(row=0, column=2, padx=15, pady=10, sticky="E")

        self.game_url.bind(
            "<FocusOut>",
            lambda *_: self.world_number_or_game_url_change(
                settings=settings, main_window=main_window
            ),
        )
        self.world_number_input.bind(
            "<FocusOut>",
            lambda *_: self.world_number_or_game_url_change(
                settings=settings, main_window=main_window
            ),
        )

        ttk.Label(self, text=translate("Currently available groups")).grid(
            row=2, column=0, padx=(15, 0), pady=(10), sticky=ttk.W
        )
        self.villages_groups = ttk.Combobox(
            self,
            state="readonly",
            justify="center",
        )
        self.villages_groups.grid(row=2, column=1, padx=(0), pady=(10))
        self.villages_groups.set(translate("Available groups"))
        self.villages_groups["values"] = settings["groups"]

        # Update available groups
        ttk.Button(
            self,
            image=main_window.images.refresh,
            bootstyle="primary.Link.TButton",
            command=lambda: threading.Thread(
                target=lambda: main_window.check_groups(settings=settings),
                name="checking_groups",
                daemon=True,
            ).start(),
        ).grid(row=2, column=2, padx=15, pady=(10), sticky=ttk.E)

        # Set language
        self.lang = {translate("English"): "en", translate("Polish"): "pl"}
        ttk.Label(self, text=translate("Application language")).grid(
            row=3, column=0, padx=(15, 0), pady=10, sticky=ttk.W
        )

        lang = ttk.StringVar()
        entries_content["globals"]["lang"] = lang

        def lang_change(*event) -> None:
            lang.get()
            for language, country_code in self.lang.items():
                if lang.get() == country_code:
                    self.set_lang.set(language)

        self.lang_trace = lang.trace_add("write", lang_change)

        def set_lang(event) -> None:
            choosed_lang = self.set_lang.get()
            lang.trace_remove("write", self.lang_trace)
            lang.set(self.lang[choosed_lang])
            lang.trace_add("write", lang_change)

        self.set_lang = ttk.Combobox(
            self, state="readonly", justify="center", width=20, values=list(self.lang)
        )
        self.set_lang.grid(row=3, column=1, pady=10)
        self.set_lang.bind("<<ComboboxSelected>>", set_lang)

        ttk.Separator(self, orient=ttk.HORIZONTAL).grid(
            row=4, column=0, columnspan=3, pady=10, sticky=ttk.EW
        )

        entries_content["globals"][
            "disable_chrome_background_throttling"
        ] = ttk.BooleanVar()
        ttk.Checkbutton(
            self,
            text=translate("Disable chrome energy saving settings"),
            variable=entries_content["globals"]["disable_chrome_background_throttling"],
        ).grid(row=5, column=0, columnspan=3, padx=15, pady=10, sticky=ttk.W)

        disable_throttling_info = ttk.Label(self, image=main_window.images.question_x24)
        disable_throttling_info.grid(row=5, column=2, padx=15, pady=10)
        ToolTip(
            disable_throttling_info,
            text=translate(
                "Energy saving settings function is turned on by default in chrome. "
                "It decrease performance for all background tasks in each tab apart from "
                "the one which is currently active or has focuse. In some rare cases it "
                "may delay some of the bot functions (from about 50-100ms up to few seconds) "
                "for example troops sending at exactly accurate time may be delayed if in "
                "the same time user browse other pages in diffrent tabs. Turnig this checkbox "
                "on will disable energy saving settings in chrome which may slitly increase "
                "browser cpu utilization but in the same time let you play tribalwars in "
                "diffrent tabs and still achieve perfect timings for bot background tasks."
                "At the same time, consider browsing other sites in a separate manually opened "
                "chrome window or another browser."
            ),
            topmost=True,
        )

        # Disable stable release
        entries_content["globals"]["stable_release"] = ttk.BooleanVar(value=True)
        ttk.Checkbutton(
            self,
            text=translate("Allow beta versions of the application"),
            onvalue=False,
            offvalue=True,
            variable=entries_content["globals"]["stable_release"],
        ).grid(row=6, columnspan=3, padx=15, pady=10, sticky=ttk.W)

        disable_stable_release_info = ttk.Label(
            self, image=main_window.images.question_x24
        )
        disable_stable_release_info.grid(row=6, column=2, padx=15, pady=10)
        ToolTip(
            disable_stable_release_info,
            text=translate(
                "Enabling this option will include the beta version of the application in the update process. "
                "These are test/development versions which, in addition to new features, may contain new unreported bugs. "
                "Recommended only for experienced users who are in contact with the creator of the bot."
            ),
            topmost=True,
        )

        # Account information

        self.acc_info_frame = ttk.Labelframe(
            self, text=translate("Account information"), labelanchor="n"
        )
        self.acc_info_frame.grid(
            row=999, column=0, columnspan=3, padx=5, pady=5, sticky=("W", "S", "E")
        )
        self.acc_info_frame.columnconfigure(0, weight=1)

        self.verified_email_label = ttk.Label(self.acc_info_frame, text="")
        self.verified_email_label.grid(
            row=1, column=0, padx=5, pady=(10, 5), sticky="S"
        )

        self.acc_expire_time = ttk.Label(self.acc_info_frame, text="acc_expire_time")
        self.acc_expire_time.grid(row=2, column=0, padx=5, pady=5, sticky="S")

        ttk.Button(
            self.acc_info_frame,
            text=translate("Extend account validity"),
            command=lambda: PaymentWindow(parent=main_window),
        ).grid(row=3, column=0, padx=5, pady=(10, 15))

    def world_number_or_game_url_change(
        self, settings: dict, main_window: "MainWindow", *args
    ) -> None:
        def on_focus_out(event: tk.Event = None) -> None:
            main_window.master.update()
            if (
                "pressed" in self.game_url.state()
                or "focus" in self.world_number_input.state()
            ):
                return

            def on_error(message: str) -> None:
                self.show()
                custom_error(message=message, parent=self.master)
                if "world_number" in settings:
                    self.entries_content["world_number"].set(settings["world_number"])

            if not self.entries_content["world_number"].get().isnumeric():
                on_error("Numer świata powinien składać się z samych cyfr.")
                return

            add_new_world(
                parent=main_window,
                settings=settings,
                game_url=self.entries_content["game_url"].get(),
                world_number=self.entries_content["world_number"].get(),
                entry_change=True,
            )

        if (
            settings["world_number"] != self.entries_content["world_number"].get()
            or settings["game_url"] != self.entries_content["game_url"].get()
        ):

            on_focus_out()
