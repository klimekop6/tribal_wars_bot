import os
import random
import re
import subprocess
import threading
import time
import tkinter as tk
from copy import deepcopy
from datetime import datetime
from functools import partial
from typing import NamedTuple

import ttkbootstrap as ttk
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchWindowException,
    UnexpectedAlertPresentException,
)
from ttkbootstrap import localization
from ttkbootstrap.tooltip import ToolTip

import app.functions as functions
import bot_functions
from app.decorators import log_errors
from app.logging import get_logger
from app.tribal_wars_bot_api import TribalWarsBotApi
from gui.functions import (
    center,
    custom_error,
    fill_entry_from_settings,
    get_pos,
    invoke_checkbuttons,
    on_button_release,
    save_entry_to_settings,
)
from gui.widgets.my_widgets import TopLevel
from gui.windows.jobs_to_do import JobsToDoWindow
from gui.windows.main_tabs.coins import Coins
from gui.windows.main_tabs.farm import Farm
from gui.windows.main_tabs.gathering import Gathering
from gui.windows.main_tabs.home import Home
from gui.windows.main_tabs.market import Market
from gui.windows.main_tabs.notifications import Notifications
from gui.windows.main_tabs.scheduler import Scheduler
from gui.windows.main_tabs.settings import Settings
from gui.windows.new_world import NewWorldWindow

translate = localization.MessageCatalog.translate

logger = get_logger(__name__)


class NavigationBar:
    def __init__(
        self, main_window: "MainWindow", settings: dict, parent: ttk.Frame = None
    ) -> None:

        self.settings = settings
        self.main_window = main_window

        self.header = ttk.Frame(parent)
        self.header.grid(row=0, column=0, pady=(5, 0), sticky=tk.NSEW)

        self.footer = ttk.Frame(parent)
        self.footer.grid(row=1, column=0, sticky=tk.NSEW)
        self.footer.columnconfigure(0, weight=1)

        # Header
        # region

        self.farm = ttk.Button(
            self.header,
            text=translate("Looting"),
            command=lambda: main_window.farm.show(),
        )
        self.farm.grid(row=1, column=0, sticky=tk.EW)

        self.gathering = ttk.Button(
            self.header,
            text=translate("Scavenging"),
            command=lambda: main_window.gathering.show(),
        )
        self.gathering.grid(row=2, column=0, sticky=tk.EW)

        self.market = ttk.Button(
            self.header,
            text=translate("Market"),
            command=lambda: main_window.market.show(),
        )
        self.market.grid(row=3, column=0, sticky=tk.EW)

        self.coins = ttk.Button(
            self.header,
            text=translate("Coins"),
            command=lambda: main_window.coins.show(),
        )
        self.coins.grid(row=4, column=0, sticky=tk.EW)

        self.schedule = ttk.Button(
            self.header,
            text=translate("Scheduler"),
            command=lambda: main_window.schedule.show(),
        )
        self.schedule.grid(row=5, column=0, sticky=tk.EW)

        self.dodge = ttk.Button(
            self.header,
            text=translate("Dodge attacks"),
            state="disabled",
            command=lambda: main_window.notifications.show(),
        )
        self.dodge.grid(row=6, column=0, sticky=tk.EW)

        self.counter_attack = ttk.Button(
            self.header,
            text=translate("Counterattack"),
            state="disabled",
            command=lambda: main_window.notifications.show(),
        )
        self.counter_attack.grid(row=7, column=0, sticky=tk.EW)

        self.manager = ttk.Button(
            self.header,
            text=translate("Account manager"),
            state="disabled",
            command=lambda: main_window.manager.show(),
        )
        self.manager.grid(row=8, column=0, sticky=tk.EW)

        self.notifications = ttk.Button(
            self.header,
            text=translate("Notifications"),
            command=lambda: main_window.notifications.show(),
        )
        self.notifications.grid(row=9, column=0, sticky=tk.EW)

        ToolTip(
            self.dodge,
            text=translate("Feature in preparation.."),
            topmost=True,
        )
        ToolTip(
            self.counter_attack,
            text=translate("Feature in preparation.."),
            topmost=True,
        )
        ToolTip(
            self.manager,
            text=translate("Feature in preparation.."),
            topmost=True,
        )

        # endregion

        # Footer

        self.home = ttk.Label(
            self.footer,
            image=main_window.images.home,
            cursor="hand2",
        )
        self.home.grid(row=1, column=0)

        def home_enter(event) -> None:
            self.home.config(image=main_window.images.home_hover)

        def home_leave(event) -> None:
            self.home.config(image=main_window.images.home)

        self.home.bind("<Enter>", home_enter)
        self.home.bind("<Leave>", home_leave)
        self.home.bind("<Button-1>", lambda _: main_window.home.show())

        self.control_panel = ttk.Label(
            self.footer,
            image=main_window.images.settings,
            cursor="hand2",
        )
        self.control_panel.grid(row=2, column=0, pady=20)

        def control_panel_enter(event) -> None:
            self.control_panel.config(image=main_window.images.settings_hover)

        def control_panel_leave(event) -> None:
            self.control_panel.config(image=main_window.images.settings)

        self.control_panel.bind("<Enter>", control_panel_enter)
        self.control_panel.bind("<Leave>", control_panel_leave)
        self.control_panel.bind(
            "<Button-1>", lambda _: main_window.control_panel.show()
        )

        # Start/stop button
        self.start_button = ttk.Label(
            self.footer, image=main_window.images.start, cursor="hand2"
        )
        self.start_button.grid(row=3, column=0, pady=(0, 20))

        def start_or_stop_bot(event) -> None:
            if not main_window.running:
                main_window.master.after_idle(self.start)
            else:
                self.stop()

        self.start_button.bind("<Enter>", self.start_button_enter)
        self.start_button.bind("<Leave>", self.start_button_leave)
        self.start_button.bind("<Button-1>", start_or_stop_bot)

    def is_entries_invalid(self) -> bool:
        self.main_window.master.update_idletasks()
        for widget in self.header.winfo_children():
            if widget.invalid:
                widget.invoke()
                return True
        return False

    def start_button_enter(self, event) -> None:
        self.start_button.config(image=self.main_window.images.start_hover)

    def start_button_leave(self, event) -> None:
        self.start_button.config(image=self.main_window.images.start)

    def stop_button_enter(self, event) -> None:
        self.start_button.config(image=self.main_window.images.stop_hover)

    def stop_button_leave(self, event) -> None:
        self.start_button.config(image=self.main_window.images.stop)

    def start(self) -> None:
        if self.is_entries_invalid():
            custom_error(
                "Wprowadzono nieprawidłowe wartości",
                parent=self.main_window.master,
            )
            return
        self.main_window.running = True
        threading.Thread(
            target=lambda: self.main_window.run(settings=self.settings),
            name="main_function",
            daemon=True,
        ).start()
        self.start_button.unbind("<Enter>")
        self.start_button.unbind("<Leave>")
        self.start_button.bind("<Enter>", self.stop_button_enter)
        self.start_button.bind("<Leave>", self.stop_button_leave)
        self.start_button.config(image=self.main_window.images.stop)

    def stop(self) -> None:
        self.main_window.running = False
        self.start_button.unbind("<Enter>")
        self.start_button.unbind("<Leave>")
        self.start_button.bind("<Enter>", self.start_button_enter)
        self.start_button.bind("<Leave>", self.start_button_leave)
        self.start_button.config(image=self.main_window.images.start)


class MainWindow:

    entries_content: dict[str, dict | tk.Variable] = {"globals": {}}
    settings_by_worlds: dict[str, dict] = {}

    def __init__(
        self,
        master: ttk.Toplevel,
        hidden_root: tk.Tk,
        settings: dict[str],
        driver: webdriver.Chrome = None,
    ) -> None:
        self.captcha_counter = ttk.IntVar()
        self.driver = driver
        self.master = master
        self.hidden_root = hidden_root
        self.running = False
        self.loading = True

        master.attributes("-alpha", 0.0)
        master.transient(hidden_root)
        master.overrideredirect(True)
        master.grid_propagate(0)
        master.geometry("620x660")
        master.configure(width=620, height=660)
        master.iconbitmap(default="icons//ikona.ico")
        master.title("Tribal Wars 24/7")

        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        # All used images -> one time load
        class Images(NamedTuple):
            # Interface labels/buttons etc.

            add: tk.PhotoImage = tk.PhotoImage(file="icons//add.png")
            add_hover: tk.PhotoImage = tk.PhotoImage(file="icons//add_hover.png")
            bin: tk.PhotoImage = tk.PhotoImage(file="icons//bin.png")
            start: tk.PhotoImage = tk.PhotoImage(file="icons//start.png")
            start_hover: tk.PhotoImage = tk.PhotoImage(file="icons//start_hover.png")
            settings_sm: tk.PhotoImage = tk.PhotoImage(file="icons//settings_sm.png")
            settings_hover_sm: tk.PhotoImage = tk.PhotoImage(
                file="icons//settings_hover_sm.png"
            )
            settings: tk.PhotoImage = tk.PhotoImage(file="icons//settings.png")
            settings_hover: tk.PhotoImage = tk.PhotoImage(
                file="icons//settings_hover.png"
            )
            stop: tk.PhotoImage = tk.PhotoImage(file="icons//stop.png")
            stop_hover: tk.PhotoImage = tk.PhotoImage(file="icons//stop_hover.png")
            exit: tk.PhotoImage = tk.PhotoImage(file="icons//exit.png")
            exit_hover: tk.PhotoImage = tk.PhotoImage(file="icons//exit_hover.png")
            minimize: tk.PhotoImage = tk.PhotoImage(file="icons//minimize.png")
            plus: tk.PhotoImage = tk.PhotoImage(file="icons//plus.png")
            refresh: tk.PhotoImage = tk.PhotoImage(file="icons//refresh.png")
            question: tk.PhotoImage = tk.PhotoImage(file="icons//question.png")
            question_x24: tk.PhotoImage = tk.PhotoImage(file="icons//question_x24.png")
            home: tk.PhotoImage = tk.PhotoImage(file="icons//home.png")
            home_hover: tk.PhotoImage = tk.PhotoImage(file="icons//home_hover.png")

            # Troops
            spear: tk.PhotoImage = tk.PhotoImage(file="icons//spear.png")
            sword: tk.PhotoImage = tk.PhotoImage(file="icons//sword.png")
            axe: tk.PhotoImage = tk.PhotoImage(file="icons//axe.png")
            archer: tk.PhotoImage = tk.PhotoImage(file="icons//archer.png")
            spy: tk.PhotoImage = tk.PhotoImage(file="icons//spy.png")
            light: tk.PhotoImage = tk.PhotoImage(file="icons//light.png")
            marcher: tk.PhotoImage = tk.PhotoImage(file="icons//marcher.png")
            heavy: tk.PhotoImage = tk.PhotoImage(file="icons//heavy.png")
            ram: tk.PhotoImage = tk.PhotoImage(file="icons//ram.png")
            catapult: tk.PhotoImage = tk.PhotoImage(file="icons//catapult.png")
            knight: tk.PhotoImage = tk.PhotoImage(file="icons//knight.png")
            snob: tk.PhotoImage = tk.PhotoImage(file="icons//snob.png")

        self.images = Images()

        # Buildings
        class Buildings(NamedTuple):
            main: str = translate("Headquarters")
            barracks: str = translate("Barracks")
            stable: str = translate("Stable")
            garage: str = translate("Workshop")
            snob: str = translate("Academy")
            smith: str = translate("Smithy")
            place: str = translate("Rally point")
            statue: str = translate("Statue")
            market: str = translate("Market")
            wood: str = translate("Timber camp")
            stone: str = translate("Clay pit")
            iron: str = translate("Iron mine")
            farm: str = translate("Farm")
            storage: str = translate("Warehouse")
            wall: str = translate("Wall")

        self.buildings = Buildings()

        # Translate ahead of time
        self.dictionary = {
            "Choose group": translate("Choose group"),
            "Verified address e-mail: Yes": translate("Verified address e-mail: Yes"),
            "Address e-mail has been werified": translate(
                "Address e-mail has been werified"
            ),
        }
        self.troops_dictionary = {
            translate("Spearman"): "spear",
            translate("Swordsman"): "sword",
            translate("Axeman"): "axe",
            translate("Archer"): "archer",
            translate("Scout"): "spy",
            translate("Light"): "light",
            translate("Marcher"): "marcher",
            translate("Heavy"): "heavy",
            translate("Ram"): "ram",
            translate("Catapult"): "catapult",
            translate("Paladin"): "knight",
            translate("Nobleman"): "snob",
        }

        # main_frame -> custom_bar, content_frame
        self.main_frame = ttk.Frame(master, borderwidth=1, relief="groove")
        self.main_frame.grid(row=0, column=0, sticky=tk.NSEW)
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(2, weight=1)

        self.custom_bar = ttk.Frame(self.main_frame)
        self.custom_bar.grid(row=0, column=0, columnspan=3, sticky=tk.EW)
        self.custom_bar.columnconfigure(3, weight=1)

        self.navigation_frame = ttk.Frame(self.main_frame)
        self.navigation_frame.grid(row=1, column=0, sticky=tk.NS)
        self.navigation_frame.rowconfigure(0, weight=1)

        ttk.Separator(self.main_frame, orient=tk.VERTICAL).grid(
            row=1, column=1, pady=(5, 0), sticky=tk.NS
        )

        self.content_frame = ttk.Frame(self.main_frame, bootstyle="info")
        self.content_frame.grid(row=1, column=2, pady=(5, 0), sticky=tk.NSEW)
        self.content_frame.rowconfigure(0, weight=1)
        self.content_frame.columnconfigure(0, weight=1)

        # custom_bar
        # region
        self.title_label = ttk.Label(self.custom_bar, text="Tribal Wars Bot")
        self.title_label.grid(row=0, column=1, padx=(5, 0), sticky="W")

        self.time = tk.StringVar()
        self.title_timer = ttk.Button(
            self.custom_bar,
            textvariable=self.time,
            bootstyle="primary.Link.TButton",
            takefocus=False,
        )

        self.entries_content["world_in_title"] = tk.StringVar(value=" ")
        self.title_world = ttk.Button(
            self.custom_bar,
            textvariable=self.entries_content["world_in_title"],
            bootstyle="primary.Link.TButton",
        )
        self.title_world.grid(row=0, column=3, padx=(5, 0), sticky="E")

        self.minimize_button = ttk.Button(
            self.custom_bar,
            bootstyle="primary.Link.TButton",
            padding=(10, 5),
            image=self.images.minimize,
            command=self.hide,
        )
        self.minimize_button.grid(row=0, column=4, padx=(5, 0), pady=5, sticky="E")

        def on_exit() -> None:
            master.withdraw()
            if self.driver:
                subprocess.run(
                    "taskkill /IM chromedriver.exe /F /T",
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            # API /logout DONE
            data = {
                "user_name": self.user_data["user_name"],
                "captcha_counter": self.captcha_counter.get(),
            }
            TribalWarsBotApi("/logout", json=data).patch(sync=False)
            if (
                "server_world" in settings
                and settings["server_world"] in self.settings_by_worlds
            ):
                save_entry_to_settings(
                    entries=self.entries_content,
                    settings=settings,
                    settings_by_worlds=self.settings_by_worlds,
                )
            else:
                save_entry_to_settings(entries=self.entries_content, settings=settings)
            settings["user_name"] = self.user_data["user_name"]
            if "user_password" in settings:
                settings["user_password"] = self.user_data["password"]
            functions.save_settings_to_files(
                settings=settings, settings_by_worlds=self.settings_by_worlds
            )
            hidden_root.destroy()

        self.exit_button = ttk.Button(
            self.custom_bar,
            style="danger.primary.Link.TButton",
            padding=(10, 5),
            image=self.images.exit,
            command=on_exit,
        )
        self.exit_button.grid(row=0, column=5, padx=(0, 5), pady=3, sticky="E")

        self.custom_bar.bind(
            "<Button-1>", lambda event: get_pos(self, event, "custom_bar")
        )
        self.title_label.bind(
            "<Button-1>", lambda event: get_pos(self, event, "title_label")
        )
        self.title_world.bind(
            "<Button-1>",
            lambda event: self.show_world_chooser_window(event, settings=settings),
        )
        bind_tags = lambda tags: (tags[2], tags[1], tags[0], tags[3])
        self.title_world.bindtags(bind_tags(self.title_world.bindtags()))

        self.title_timer.bind(
            "<Button-1>", lambda event: self.show_jobs_to_do_window(event)
        )
        # endregion

        # navigation_bar

        self.navigation = NavigationBar(
            self, parent=self.navigation_frame, settings=settings
        )

        # content_frame

        self.home = Home(
            parent=self.content_frame,
            main_window=self,
            entries_content=self.entries_content,
            settings=settings,
        )

        self.farm = Farm(
            parent=self.content_frame,
            main_window=self,
            entries_content=self.entries_content,
            settings=settings,
        )

        self.gathering = Gathering(
            parent=self.content_frame,
            main_window=self,
            entries_content=self.entries_content,
            settings=settings,
        )

        self.schedule = Scheduler(
            parent=self.content_frame,
            main_window=self,
            entries_content=self.entries_content,
            settings=settings,
        )

        self.market = Market(
            parent=self.content_frame,
            main_window=self,
            entries_content=self.entries_content,
            settings=settings,
        )

        self.coins = Coins(
            parent=self.content_frame,
            main_window=self,
            entries_content=self.entries_content,
            settings=settings,
        )

        self.control_panel = Settings(
            parent=self.content_frame,
            main_window=self,
            entries_content=self.entries_content,
            settings=settings,
        )

        # self.manager = Manager(
        #     parent=self.content_frame,
        #     main_window=self,
        #     entries_content=self.entries_content,
        #     settings=settings,
        # )

        self.notifications = Notifications(
            parent=self.content_frame,
            main_window=self,
            entries_content=self.entries_content,
            settings=settings,
        )

        # Other things
        fill_entry_from_settings(entries=self.entries_content, settings=settings)
        save_entry_to_settings(entries=self.entries_content, settings=settings)

        self.set_bindings(master=master, hidden_root=hidden_root)

    def check_groups(self, settings: dict):

        if "server_world" not in settings:
            self.control_panel.show()
            custom_error(
                message="Najpierw wybierz serwer i numer świata",
                parent=self.control_panel.master,
            )
            return
        self.control_panel.villages_groups.set("Updating..")
        save_entry_to_settings(entries=self.entries_content, settings=settings)
        functions.check_groups(
            driver=self.driver,
            settings=settings,
            widgets=[
                self.farm.farm_group_A,
                self.farm.farm_group_B,
                self.farm.farm_group_C,
                self.gathering.gathering_group,
                self.control_panel.villages_groups,
            ],
        )
        self.control_panel.villages_groups.set("Available groups")

    @log_errors()
    def change_world(
        self, server_world: str, world_in_title: str, settings: dict
    ) -> None:

        # Skip if user clicked/choose the same world as he is now
        if server_world == settings["server_world"]:
            if hasattr(self, "world_chooser_window"):
                self.world_chooser_window.destroy()
            return

        # Change if already exist in self.settings_by_worlds
        if server_world in self.settings_by_worlds:
            # Save current settings before changing to other
            if settings["server_world"] in self.settings_by_worlds:
                save_entry_to_settings(
                    entries=self.entries_content,
                    settings=settings,
                    settings_by_worlds=self.settings_by_worlds,
                )
            settings.update(self.settings_by_worlds[server_world])

            # assert settings == self.settings_by_worlds[server_world]

            # Set available groups
            self.farm.farm_group_A["values"] = settings["groups"]
            self.farm.farm_group_B["values"] = settings["groups"]
            self.farm.farm_group_C["values"] = settings["groups"]
            self.gathering.gathering_group["values"] = settings["groups"]
            self.control_panel.villages_groups["values"] = settings["groups"]

            # Refresh schedule window
            self.schedule.redraw_availabe_templates(settings=settings)

            # Refresh coins window with choosed villages
            self.coins.redraw_choosed_villges()

            fill_entry_from_settings(entries=self.entries_content, settings=settings)

            # Usuwa z listy nieaktualne terminy wysyłki wojsk (których termin już upłynął)
            schedule = self.settings_by_worlds[server_world]["scheduler"][
                "ready_schedule"
            ]
            if schedule:
                current_time = time.time()
                schedule = [
                    value for value in schedule if value["send_time"] > current_time
                ]

            invoke_checkbuttons(parent=self.master, main_window=self)
            self.schedule.fake_troops.invoke()
            self.schedule.template_type.set("")

            self.entries_content["world_in_title"].set(f"{world_in_title}")
            self.world_chooser_window.destroy()

    def hide(self):
        self.master.attributes("-alpha", 0.0)
        self.hidden_root.iconify()

        def show(event=None):
            self.master.attributes("-alpha", 1.0)

        self.master.bind("<Map>", show)

    @log_errors(send_email=True)
    def run(self, settings: dict):
        """Uruchamia całego bota"""

        def on_func_stop() -> None:
            self.navigation.stop()

        save_entry_to_settings(
            entries=self.entries_content,
            settings=settings,
            settings_by_worlds=self.settings_by_worlds,
        )

        # E-mail verification
        if not self.user_data["verified_email"]:
            if hasattr(self, "verify_window"):
                if self.verify_window.winfo_exists():
                    self.verify_window.destroy()
            self.verify_window = TopLevel(title_text="Weryfikacja adresu e-mail")
            content_frame = self.verify_window.content_frame
            content_frame.columnconfigure(1, weight=1)

            ttk.Label(content_frame, text="Kod weryfikacyjny: ").grid(
                row=0, column=0, padx=(25, 0), pady=10
            )
            verification_code_entry = ttk.Entry(
                content_frame, width=8, justify="center"
            )
            verification_code_entry.grid(row=0, column=1, padx=(0, 25), pady=10)

            def verify_email():
                if verification_code_entry.get() == self.user_data["verification_code"]:
                    # API PATCH /user/<user_name> DONE
                    data = {"verified_email": 1}
                    TribalWarsBotApi(
                        f"/user?user_name={self.user_data['user_name']}", json=data
                    ).patch(sync=False)
                    # API PATCH /bonus DONE
                    if (
                        not self.user_data["bonus_email"]
                        and self.user_data["invited_by"]
                    ):
                        data = {
                            "user_name": self.user_data["user_name"],
                            "invited_by": self.user_data["invited_by"],
                        }
                        TribalWarsBotApi("/bonus", json=data).patch(sync=False)
                    self.user_data["verified_email"] = True
                    self.control_panel.verified_email_label.config(
                        text=self.dictionary["Verified address e-mail: Yes"]
                    )
                    custom_error(
                        message=self.dictionary["Address e-mail has been werified"],
                        parent=self.verify_window,
                    )
                    self.verify_window.destroy()
                    return

                ttk.Label(
                    content_frame, text="Nieprawidłowy kod", bootstyle="danger"
                ).grid(
                    row=1,
                    column=0,
                    columnspan=2,
                    padx=5,
                    pady=(0, 5),
                )
                verification_code_entry.configure(bootstyle="danger")
                verification_code_entry.bind(
                    "<FocusIn>",
                    lambda _: verification_code_entry.config(bootstyle="default"),
                )

            verify_button = ttk.Button(
                content_frame, text="Weryfikuj", command=verify_email
            )
            verify_button.grid(
                row=2, column=0, columnspan=2, padx=5, pady=(10, 5), sticky=tk.EW
            )

            verification_code_entry.bind("<Return>", lambda _: verify_button.invoke())

            center(window=self.verify_window, parent=self.master)

            self.verify_window.attributes("-alpha", 1.0)
            # verify_button.wait_window(self.verify_window)

            on_func_stop()
            return

        # Check if_paid
        if not functions.paid(str(self.user_data["active_until"])):
            response = TribalWarsBotApi(
                f"/user?user_name={self.user_data['user_name']}"
            ).get()
            if not response.ok:
                custom_error(
                    message="Serwer jest tymczasowo niedostępny.\n"
                    "Proszę spróbować ponownie za chwilę.",
                    parent=self.master,
                )
                on_func_stop()
                return
            self.user_data = response.json()
            if not functions.paid(str(self.user_data["active_until"])):
                custom_error(
                    message="Ważność konta wygasła.\n"
                    "Przejdź do ustawień i kliknij przedłuż ważność konta.",
                    parent=self.master,
                )
                on_func_stop()
                return
            self.control_panel.acc_expire_time.config(
                text=f'Konto ważne do {self.user_data["active_until"]}'
            )

        # Check if user choosed/set any game server
        if "server_world" not in settings:
            self.control_panel.show()
            if "Wybierz serwer" in self.control_panel.game_url.get():
                self.control_panel.game_url.configure(bootstyle="danger")
            if not self.control_panel.world_number_input.get().strip():
                self.control_panel.world_number_input.configure(bootstyle="danger")
            custom_error(
                message="Najpierw wybierz serwer i numer świata", parent=self.master
            )
            on_func_stop()
            return

        # Check if user set properly settings
        for (
            server_world,
            _settings,
        ) in self.settings_by_worlds.items():  # server_world = de199, pl173 etc.
            # Check if group was choosed
            # Farm group
            if _settings["farm_group"] == self.dictionary["Choose group"]:
                if any(_settings[letter]["active"] for letter in ("A", "B", "C")):
                    self.change_world(
                        server_world=server_world,
                        world_in_title=_settings["world_in_title"],
                        settings=settings,
                    )
                    self.farm.show()
                    custom_error(
                        message="Nie wybrano grupy wiosek do farmienia.",
                        parent=self.master,
                    )
                    on_func_stop()
                    return
            # Gathering group
            if _settings["gathering_group"] == self.dictionary["Choose group"]:
                if _settings["gathering"]["active"]:
                    self.change_world(
                        server_world=server_world,
                        world_in_title=_settings["world_in_title"],
                        settings=settings,
                    )
                    self.gathering.show()
                    custom_error(
                        message="Nie wybrano grupy wiosek do zbieractwa.",
                        parent=self.gathering.master,
                    )
                    on_func_stop()
                    return

            # Check if user set sleep value bigger than 0 in choosed functions
            # Auto farm sleep time
            if _settings["farm_sleep_time"] == 0 and any(
                _settings[template]["active"] for template in ("A", "B", "C")
            ):
                self.farm.show()
                self.change_world(
                    server_world=server_world,
                    world_in_title=_settings["world_in_title"],
                    settings=settings,
                )
                custom_error(
                    message='Ustaw pole "Powtarzaj ataki w odstępach [min]".',
                    parent=self.farm.master,
                )
                on_func_stop()
                return
            # Market sleep time between each function call/run
            if (
                _settings["market"]["premium_exchange"]
                and _settings["market"]["check_every"] == 0
            ):
                self.change_world(
                    server_world=server_world,
                    world_in_title=_settings["world_in_title"],
                    settings=settings,
                )
                self.market.show()
                custom_error(
                    message='Ustaw pole "Sprawdzaj kurs co [min]".',
                    parent=self.market.master,
                )
                on_func_stop()
                return
            # Mining coins sleep time

            if (
                _settings["coins"]["mine_coin"]
                and _settings["coins"]["check_every"] == 0
            ):
                self.change_world(
                    server_world=server_world,
                    world_in_title=_settings["world_in_title"],
                    settings=settings,
                )
                self.coins.show()
                custom_error(
                    message='Ustaw pole "Wybijaj monety i wzywaj surowce co [min]".',
                    parent=self.coins.master,
                )
                on_func_stop()
                return
            # Incoming attacks sleep time
            if (
                _settings["notifications"]["check_incoming_attacks_sleep_time"] == 0
                and _settings["notifications"]["check_incoming_attacks"]
            ):
                self.change_world(
                    server_world=server_world,
                    world_in_title=_settings["world_in_title"],
                    settings=settings,
                )
                self.notifications.show()
                custom_error(
                    message='Ustaw pole "Twórz etykiety ataków co [min]".',
                    parent=self.notifications.master,
                )
                on_func_stop()
                return

        self.to_do = []

        incoming_attacks = False
        logged = False

        # Add functions into to_do list
        for server_world in self.settings_by_worlds:  # server_world = de199, pl173 etc.
            if (
                server_world in settings["globals"]
                and not settings["globals"][server_world]
            ):
                continue
            _settings = self.settings_by_worlds[server_world]
            _settings["temp"] = {
                "main_window": self,
                "to_do": self.to_do,
                "captcha_counter": self.captcha_counter,
            }
            to_do = []
            # Add daily bonus check
            if _settings["world_config"]["daily_bonus"] != False:
                to_do.append({"func": "daily_bonus"})
            # Add farm
            if (
                _settings["A"]["active"]
                | _settings["B"]["active"]
                | _settings["C"]["active"]
            ):
                to_do.append({"func": "auto_farm"})
                # Make sure there is added new features
                for template in ("A", "B", "C"):
                    if "farm_rules" not in _settings[template]:
                        _settings[template]["farm_rules"] = {}
                    if "max_travel_time" not in _settings[template]["farm_rules"]:
                        _settings[template]["farm_rules"]["max_travel_time"] = 0
                    if "loot" not in _settings[template]["farm_rules"]:
                        _settings[template]["farm_rules"]["loot"] = "mix_loot"

            # Add gathering
            if _settings["gathering"]["active"]:
                to_do.append({"func": "gathering"})
            # Add check incoming attacks
            if _settings["notifications"]["check_incoming_attacks"]:
                to_do.append({"func": "check_incoming_attacks"})
            # Premium exchange
            if _settings["market"]["premium_exchange"]:
                to_do.append({"func": "premium_exchange"})
            # Mine coins
            if "mine_coin" in _settings["coins"] and _settings["coins"]["mine_coin"]:
                to_do.append({"func": "mine_coin"})

            # Add start_time and other settings for above functions
            server_world = _settings["server_world"]
            for func in to_do:
                func["start_time"] = time.time()
                func["server_world"] = server_world
                func["settings"] = _settings
                func["errors_number"] = 0

            # Usuwa z listy nieaktualne terminy wysyłki wojsk (których termin już upłynął)
            if _settings["scheduler"]["ready_schedule"]:
                current_time = time.time()
                _settings["scheduler"]["ready_schedule"] = [
                    value
                    for value in _settings["scheduler"]["ready_schedule"]
                    if value["send_time"] > current_time
                ]
                # Dodaj planer do listy to_do
                for send_info in _settings["scheduler"]["ready_schedule"]:
                    to_do.append(
                        {
                            "func": "send_troops",
                            "start_time": send_info["send_time"] - 8,
                            "server_world": _settings["server_world"],
                            "settings": _settings,
                            "errors_number": 0,
                        }
                    )

            self.to_do.extend(to_do)
        if not len(self.to_do):
            on_func_stop()
            custom_error(message="Brak zadań do wykonania", parent=self.master)
            return
        self.to_do.sort(key=lambda sort_by: sort_by["start_time"])

        # Functions to use in main loop
        def log_out_when_free_time(_settings: dict) -> bool:
            """Log out if there won't be anything to do soon.

            Return False on log out or True if not
            """

            if self.to_do:
                if self.to_do[0]["start_time"] > time.time() + 300:
                    self.driver.get("chrome://newtab")
                    return False
                if _settings["server_world"] == self.to_do[0]["server_world"]:
                    return True
                if self.to_do[0]["start_time"] > time.time() + 5:
                    self.driver.get("chrome://newtab")
                return False
            return True

        def restart_browser() -> None:
            nonlocal logged

            logger.info(f"restarting browser coused by {self.to_do[0]['func']}")
            self.driver.quit()
            self.driver = functions.run_driver(settings=settings)
            logged = functions.log_in(self.driver, _settings)

        # Open browser if not already opend
        if not self.driver:
            self.driver = functions.run_driver(settings=settings)

        # Grid and set timer in custombar
        self.title_timer.grid(row=0, column=2, padx=5)
        self.time.set("Running..")

        # Główna pętla
        while self.running:
            if not self.to_do:
                self.running = False
                custom_error(
                    message="Wszystkie zadania zostały wykonane", parent=self.master
                )
                break

            # Jeżeli zostało trochę czasu do wykonania najbliższego zadania
            # Uruchamia timer w oknie głównym i oknie zadań (jeśli istnieje)
            time_left = self.to_do[0]["start_time"] - time.time()
            settings_send_amount = len(settings["scheduler"]["ready_schedule"])
            while time_left > 0 and self.running:
                try:
                    # Update to_do after user delete something in schedule
                    if settings_send_amount != len(
                        settings["scheduler"]["ready_schedule"]
                    ):
                        current_settings_send_amount = len(
                            settings["scheduler"]["ready_schedule"]
                        )
                        # If user added something -> update settings_send_amount and continue
                        if current_settings_send_amount > settings_send_amount:
                            settings_send_amount = current_settings_send_amount
                            continue
                        index_to_del = []
                        amount_to_del = (
                            settings_send_amount - current_settings_send_amount
                        )
                        for index, task in enumerate(self.to_do):
                            if task["func"] != "send_troops":
                                continue
                            if task["server_world"] != settings["server_world"]:
                                continue
                            for schedule in settings["scheduler"]["ready_schedule"]:
                                # Break if find in schedule with the same send_time with ms accuracy
                                if task["start_time"] + 8 == schedule["send_time"]:
                                    break
                            else:
                                index_to_del.append(index)
                                if amount_to_del == len(index_to_del):
                                    break
                        for index in reversed(index_to_del):
                            del self.to_do[index]
                        settings_send_amount = current_settings_send_amount

                    if not functions.paid(str(self.user_data["active_until"])):
                        response = TribalWarsBotApi(
                            f"/user?user_name={self.user_data['user_name']}"
                        ).get()
                        if not response.ok:
                            for wait in (5, 15, 30, 60, 300):
                                time.sleep(wait)
                                response = TribalWarsBotApi(
                                    f"/user?user_name={self.user_data['user_name']}"
                                ).get()
                                if response.ok:
                                    break
                        if response.ok:
                            self.user_data = response.json()
                        if not functions.paid(str(self.user_data["active_until"])):
                            self.running = False
                            break
                        self.control_panel.acc_expire_time.config(
                            text=f'Konto ważne do {self.user_data["active_until"]}'
                        )
                    # Timer -> odliczanie czasu do najbliższego zadania
                    self.time.set(
                        f"{time.strftime('%H:%M:%S', time.gmtime(time_left))}"
                    )
                    time.sleep(0.33)
                    if not self.to_do:
                        break
                    time_left = self.to_do[0]["start_time"] - time.time()
                except Exception:
                    functions.log_error(self.driver)

            if not self.running:
                break
            if not self.to_do:
                continue

            self.time.set("Running..")

            _settings = self.to_do[0]["settings"]

            # Deleguję zadania na podstawie dopasowań self.to_do[0]["func"]
            try:
                try:
                    if not logged:
                        logged = functions.log_in(self.driver, _settings)

                    try:
                        functions.captcha_check(self.driver, _settings)
                    except Exception:
                        pass

                    match self.to_do[0]["func"]:

                        case "auto_farm":
                            bot_functions.auto_farm(self.driver, _settings)
                            self.to_do[0]["start_time"] = time.time() + _settings[
                                "farm_sleep_time"
                            ] * random.uniform(52, 68)
                            self.to_do[0]["errors_number"] = 0
                            self.to_do.append(self.to_do[0])

                        case "check_incoming_attacks":
                            bot_functions.attacks_labels(self.driver, _settings)
                            self.to_do[0]["start_time"] = time.time() + _settings[
                                "notifications"
                            ]["check_incoming_attacks_sleep_time"] * random.uniform(
                                58, 62
                            )
                            self.to_do[0]["errors_number"] = 0
                            self.to_do.append(self.to_do[0])

                        case "daily_bonus":
                            if bot_functions.open_daily_bonus(self.driver, _settings):
                                current_time = datetime.today()
                                sec_to_midnight = (
                                    (23 - current_time.hour) * 3600
                                    + (59 - current_time.minute) * 60
                                    + (59 - current_time.second)
                                    + 2
                                )
                                self.to_do[0]["start_time"] = (
                                    time.time() + sec_to_midnight
                                )
                                self.to_do[0]["errors_number"] = 0
                                self.to_do.append(self.to_do[0])

                        case "gathering":
                            incoming_attacks = False
                            if _settings["gathering"]["stop_if_incoming_attacks"]:
                                incoming_attacks = bot_functions.attacks_labels(
                                    self.driver, _settings
                                )
                            if not _settings["gathering"][
                                "stop_if_incoming_attacks"
                            ] or (
                                _settings["gathering"]["stop_if_incoming_attacks"]
                                and not incoming_attacks
                            ):
                                # List of dicts contains dicts ready to add into to_do list
                                list_of_dicts = bot_functions.gathering_resources(
                                    driver=self.driver, **self.to_do[0]
                                )
                                for _dict in list_of_dicts:
                                    self.to_do.append(_dict)

                        case "mine_coin":
                            bot_functions.mine_coin(
                                driver=self.driver, settings=_settings
                            )
                            self.to_do[0]["start_time"] = time.time() + _settings[
                                "coins"
                            ]["check_every"] * random.uniform(50, 70)
                            self.to_do[0]["errors_number"] = 0
                            self.to_do.append(self.to_do[0])

                        case "premium_exchange":
                            bot_functions.premium_exchange(self.driver, _settings)
                            self.to_do[0]["start_time"] = time.time() + _settings[
                                "market"
                            ]["check_every"] * random.uniform(50, 70)
                            self.to_do[0]["errors_number"] = 0
                            self.to_do.append(self.to_do[0])

                        case "send_troops":
                            (
                                send_number_times,
                                attacks_to_repeat,
                            ) = bot_functions.send_troops(self.driver, _settings)

                            # Clean from _settings
                            del _settings["scheduler"]["ready_schedule"][
                                0:send_number_times
                            ]
                            if attacks_to_repeat:
                                _settings["scheduler"]["ready_schedule"].sort(
                                    key=lambda x: x["send_time"]
                                )

                            if send_number_times > 1:
                                index_to_del = []
                                for index, row_data in enumerate(self.to_do):
                                    if row_data["func"] != "send_troops":
                                        continue
                                    if (
                                        row_data["server_world"]
                                        != _settings["server_world"]
                                    ):
                                        continue
                                    index_to_del.append(index)
                                    if len(index_to_del) == send_number_times:
                                        break
                                for index in sorted(index_to_del, reverse=True)[:-1]:
                                    del self.to_do[index]
                            for attack in attacks_to_repeat:
                                self.to_do.append(attack)

                    del self.to_do[0]
                    self.to_do.sort(key=lambda sort_by: sort_by["start_time"])
                    # Aktualizacja listy zadań jeśli okno zadań jest aktualnie wyświetlone
                    if hasattr(self, "jobs_info"):
                        if hasattr(self.jobs_info, "master"):
                            if self.jobs_info.master.winfo_exists():
                                self.jobs_info.update_table(main_window=self)
                except NoSuchWindowException as e:
                    logger.info("NoSuchWindowException")
                    try:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                    except Exception as e:
                        subprocess.run(
                            "taskkill /IM chromedriver.exe /F /T",
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                        self.driver = functions.run_driver(settings=settings)
                    logged = functions.log_in(self.driver, _settings)
                except UnexpectedAlertPresentException:
                    logger.info("UnexpectedAlertPresentException")
                    self.to_do[0]["errors_number"] += 1
                    if self.to_do[0]["errors_number"] > 2:
                        restart_browser()
                        continue
                    self.driver.switch_to.alert.dismiss()
                    self.driver.switch_to.default_content()
                except Exception as e:
                    # WebDriverException
                    if "chrome not reachable" in str(e):
                        logger.error("Chrome is not reachable error", exc_info=True)
                        subprocess.run(
                            "taskkill /IM chromedriver.exe /F /T",
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                        self.driver = functions.run_driver(settings=settings)
                        logged = functions.log_in(self.driver, _settings)
                        continue
                    if "cannot determine loading status" in str(e):
                        continue
                    # Skip 1st func in self.to_do if can't run it properly
                    self.to_do[0]["errors_number"] += 1
                    # Only for func send_troops
                    if (
                        self.to_do[0]["errors_number"] > 1
                        and self.to_do[0]["func"] == "send_troops"
                    ):
                        del self.to_do[0]
                        del _settings["scheduler"]["ready_schedule"][0]
                        logged = log_out_when_free_time(_settings)
                    # For all other funcs than send_troops
                    if self.to_do[0]["errors_number"] > 9:
                        del self.to_do[0]
                        logged = log_out_when_free_time(_settings)

                    if not logged:
                        continue

                    html = self.driver.page_source

                    # Deal with known things like popups, captcha etc.
                    if (
                        functions.unwanted_page_content(self.driver, _settings, html)
                        or self.to_do[0]["errors_number"] % 2 == 1
                    ):
                        continue

                    # Unknown error
                    restart_browser()
                    continue
            except Exception:
                logger.info(f"Fatal error occured")
            # Zamyka stronę plemion jeśli do następnej czynności pozostało więcej niż 5min
            logged = log_out_when_free_time(_settings)

        # Zapis ustawień gdy bot zostanie ręcznie zatrzymany
        on_func_stop()
        self.time.set("")
        self.title_timer.grid_remove()

    def set_bindings(self, master: ttk.Toplevel, hidden_root: tk.Tk) -> None:
        master.unbind_class("TCombobox", "<MouseWheel>")

        master.bind_class("TEntry", "<FocusIn>", on_button_release, add="+")
        master.bind_class("TSpinbox", "<FocusIn>", on_button_release, add="+")

        def on_main_window_click(event: tk.Event):
            if master.focus_get() is None:
                hidden_root.focus_force()
                master.update_idletasks()
            x, y = master.winfo_pointerxy()
            widget = master.winfo_containing(x, y)
            if all(w_type not in str(widget) for w_type in (".!text", ".!entry")):
                master.focus()
            else:
                if master.focus_get() != widget:
                    widget.focus_set()
            if "combobox" not in str(widget):
                master.lift()

        master.bind_class(
            "TEntry",
            "<FocusOut>",
            lambda event: event.widget.selection_clear(),
            add="+",
        )
        master.bind_class(
            "TSpinbox",
            "<FocusOut>",
            lambda event: event.widget.selection_clear(),
            add="+",
        )

        master.bind("<Button-1>", on_main_window_click, add="+")
        master.withdraw()

        def on_visibility(event):
            master.lift()

        hidden_root.bind("<Visibility>", on_visibility)

    def show_jobs_to_do_window(self, event) -> None:

        if hasattr(self, "jobs_info"):
            if hasattr(self.jobs_info, "master"):
                if self.jobs_info.master.winfo_exists():
                    self.jobs_info.master.deiconify()
                    center(self.jobs_info.master, self.master)
                    return

        self.jobs_info = JobsToDoWindow(main_window=self)

    def show_world_chooser_window(self, event, settings: dict) -> None:
        """Show new window with available worlds settings to choose"""

        def add_world() -> None:
            self.world_chooser_window.destroy()
            NewWorldWindow(self, settings=settings)

        def delete_world(server_world: str) -> None:

            master = TopLevel(title_text="Tribal Wars Bot")

            content_frame = master.content_frame
            content_frame.columnconfigure(1, weight=1)

            ttk.Label(
                content_frame,
                text=f"Czy chcesz usunąć ustawienia {server_world}?",
            ).grid(row=0, column=0, columnspan=2, padx=5, pady=5)

            exit_var = ttk.BooleanVar()
            ttk.Button(
                content_frame,
                text="Tak",
                command=lambda: [exit_var.set(1), master.destroy()],
            ).grid(row=1, column=0, padx=5, pady=5, sticky=ttk.NSEW)
            ttk.Button(
                content_frame,
                text="Nie",
                command=lambda: [exit_var.set(0), master.destroy()],
            ).grid(row=1, column=1, padx=5, pady=5, sticky=ttk.NSEW)

            center(window=master, parent=self.world_chooser_window)
            master.attributes("-alpha", 1.0)
            master.wait_window()

            if not exit_var.get():
                return

            if os.path.exists(f"settings/{server_world}.json"):
                os.remove(f"settings/{server_world}.json")
            del settings["globals"][server_world]
            del self.entries_content["globals"][server_world]
            if server_world in self.settings_by_worlds:
                del self.settings_by_worlds[server_world]

            self.world_chooser_window.destroy()

        def on_leave(event: tk.Event) -> None:
            if event.widget != self.world_chooser_window:
                return

            def on_enter(event: tk.Event) -> None:
                if event.widget != self.world_chooser_window:
                    return
                self.master.unbind("<Button-1>", self.title_world_func_id)
                del self.title_world_func_id

            self.title_world_func_id = self.master.bind(
                "<Button-1>", lambda _: self.world_chooser_window.destroy(), "+"
            )
            self.world_chooser_window.bind("<Enter>", on_enter)

        def on_destroy(event: tk.Event = None) -> None:
            self.world_chooser_window.unbind("<Destroy>")
            self.master.unbind("<Unmap>")
            if hasattr(self, "title_world_func_id"):
                self.master.unbind("<Button-1>", self.title_world_func_id)
                del self.title_world_func_id

        self.world_chooser_window = ttk.Toplevel(
            self.title_world, borderwidth=2, relief="groove"
        )
        self.world_chooser_window.attributes("-alpha", 0.0)
        self.world_chooser_window.overrideredirect(True)

        if not self.settings_by_worlds and "server_world" in settings:
            save_entry_to_settings(entries=self.entries_content, settings=settings)
            if settings["server_world"] not in self.settings_by_worlds:
                self.settings_by_worlds[settings["server_world"]] = deepcopy(settings)

        for index, server_world in enumerate(self.settings_by_worlds):
            country_code = re.search(r"\D+", server_world).group()
            world_in_title = server_world.replace(country_code, country_code.upper())
            self.entries_content["globals"][server_world] = ttk.BooleanVar(value=True)
            if server_world in settings["globals"]:
                self.entries_content["globals"][server_world].set(
                    settings["globals"][server_world]
                )

            def update_settings(server_world) -> None:

                settings["globals"][server_world] = self.entries_content["globals"][
                    server_world
                ].get()

            ttk.Checkbutton(
                self.world_chooser_window,
                offvalue=False,
                onvalue=True,
                variable=self.entries_content["globals"][server_world],
                command=partial(update_settings, server_world),
            ).grid(row=index * 2, column=0, padx=(8, 2), sticky=ttk.NSEW)
            ttk.Button(
                self.world_chooser_window,
                bootstyle="primary.Link.TButton",
                text=f"{world_in_title}",
                command=partial(
                    self.change_world, server_world, world_in_title, settings
                ),
            ).grid(row=index * 2, column=2, sticky=ttk.NSEW)

            ttk.Button(
                self.world_chooser_window,
                style="danger.primary.Link.TButton",
                image=self.images.exit,
                command=partial(delete_world, server_world),
            ).grid(row=index * 2, column=4, sticky=ttk.NSEW)

            ttk.Separator(self.world_chooser_window, style="default.TSeparator").grid(
                row=index * 2 + 1, column=0, columnspan=5, sticky=ttk.EW
            )

        ttk.Separator(
            self.world_chooser_window,
            orient=ttk.VERTICAL,
            style="default.TSeparator",
        ).grid(
            row=0, rowspan=len(self.settings_by_worlds) * 2 - 1, column=1, sticky=ttk.NS
        )
        ttk.Separator(
            self.world_chooser_window,
            orient=ttk.VERTICAL,
            style="default.TSeparator",
        ).grid(
            row=0, rowspan=len(self.settings_by_worlds) * 2 - 1, column=3, sticky=ttk.NS
        )

        add_world_button = ttk.Button(
            self.world_chooser_window,
            image=self.images.plus,
            bootstyle="primary.Link.TButton",
            command=add_world,
        )
        add_world_button.grid(
            row=len(self.settings_by_worlds) * 2,
            column=0,
            columnspan=5,
            sticky=ttk.NSEW,
        )

        self.master.bind("<Unmap>", lambda _: self.world_chooser_window.destroy())
        self.world_chooser_window.bind("<Leave>", on_leave)
        self.world_chooser_window.bind("<Destroy>", on_destroy)
        center(self.world_chooser_window, self.title_world)
        self.world_chooser_window.attributes("-alpha", 1.0)
        self.world_chooser_window.after_idle(
            lambda: self.world_chooser_window.attributes("-topmost", 1)
        )
