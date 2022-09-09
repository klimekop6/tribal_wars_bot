import json
import logging
import os

if not os.path.exists("logs"):
    os.mkdir("logs")
import random
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from copy import deepcopy
from datetime import datetime, timedelta
from functools import partial
from math import sqrt
from pathlib import Path
from typing import NamedTuple

import requests
import ttkbootstrap as ttk
import xmltodict
from pyupdater.client import Client
from selenium import webdriver
from selenium.common.exceptions import NoSuchWindowException
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.toast import ToastNotification
from ttkbootstrap.tooltip import ToolTip

import app_functions
import bot_functions
from app_logging import CustomLogFormatter, get_logger
from client_config import ClientConfig
from decorators import log_errors
from gui_functions import (
    center,
    change_state,
    custom_error,
    fill_entry_from_settings,
    forget_row,
    get_pos,
    invoke_checkbuttons,
    on_button_release,
    save_entry_to_settings,
)
from log_in_window import LogInWindow
from my_widgets import ScrollableFrame, TopLevel
from tribal_wars_bot_api import TribalWarsBotApi

os.environ["WDM_LOG"] = "false"

# Change root logger path file
root_logger = logging.getLogger("")
root_logger.handlers = []
root_format = CustomLogFormatter(
    "%(levelname)s:%(name)s:%(message)s", datefmt="%d-%m-%Y %H:%M:%S"
)
root_handler = logging.FileHandler("logs/pyu.txt")
root_handler.setFormatter(root_format)
root_handler.setLevel(logging.DEBUG)
root_logger.addHandler(root_handler)

# Default app log file
logger = get_logger(__name__)

# Log debug if debug.txt file exist
if os.path.exists("logs/debug.txt"):
    debug_handler = logging.FileHandler("logs/debug.txt")
    f_format = CustomLogFormatter(
        "%(levelname)s | %(name)s | %(asctime)s %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S",
    )
    debug_handler.setFormatter(f_format)
    debug_handler.setLevel(logging.DEBUG)
    logger.addHandler(debug_handler)
    logger.setLevel(logging.DEBUG)

logger.propagate = False


class Farm(ScrollableFrame):
    """Content and functions to put in notebook frame f1 named 'Farma'."""

    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ) -> None:
        super().__init__(parent)

        self.entries_content = entries_content

        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=0)

        templates = ttk.Notebook(self.frame)
        templates.grid(row=0, column=0, pady=5, padx=5, sticky=tk.NSEW)

        # Create notebooks for for all templates A, B, C
        for template in ("A", "B", "C"):
            self.__setattr__(f"master_{template}", ttk.Frame(templates))
            master: ttk.Frame = self.__getattribute__(f"master_{template}")
            master.columnconfigure(0, weight=1)
            master.columnconfigure(1, weight=1)
            templates.add(master, text=f"Szablon {template}")

            self.entries_content[template] = {}

            self.entries_content[template]["active"] = tk.BooleanVar()
            self.__setattr__(
                f"active_{template}",
                ttk.Checkbutton(
                    master,
                    text="Aktywuj szablon",
                    variable=self.entries_content[template]["active"],
                    onvalue=True,
                    offvalue=False,
                ),
            )
            active: ttk.Checkbutton = self.__getattribute__(f"active_{template}")
            active.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
            active.configure(
                command=partial(
                    change_state,
                    master,
                    "active",
                    self.entries_content[template],
                    True,
                    active,
                )
            )

            ttk.Separator(master, orient="horizontal").grid(
                row=1, column=0, columnspan=2, sticky=("W", "E")
            )

            self.__setattr__(f"{template}_frame", ttk.Frame(master))
            frame: ttk.Frame = self.__getattribute__(f"{template}_frame")
            frame.grid(row=2, columnspan=2, sticky="EW", padx=0, pady=20)
            frame.columnconfigure(1, weight=1)

            if "farm_group" not in self.entries_content:
                self.entries_content["farm_group"] = tk.StringVar()
            ttk.Label(frame, text="Grupa farmiąca").grid(
                row=0, column=0, padx=(5, 0), pady=(10), sticky="W"
            )
            self.__setattr__(
                f"farm_group_{template}",
                ttk.Combobox(
                    frame,
                    textvariable=self.entries_content["farm_group"],
                    state="readonly",
                    justify="center",
                ),
            )
            farm_group: ttk.Combobox = self.__getattribute__(f"farm_group_{template}")
            farm_group.grid(row=0, column=1, padx=(0), pady=(10))
            farm_group.set("Wybierz grupę")
            farm_group["values"] = settings["groups"]

            ttk.Button(
                frame,
                image=main_window.images.refresh,
                bootstyle="primary.Link.TButton",
                command=lambda: threading.Thread(
                    target=lambda: main_window.check_groups(settings=settings),
                    name="checking_groups",
                    daemon=True,
                ).start(),
            ).grid(row=0, column=2, padx=(0, 25), pady=(10), sticky="E")

            ttk.Label(master, text="Poziom muru").grid(
                row=4, column=0, columnspan=2, pady=(0, 15), padx=5, sticky="W"
            )

            self.entries_content[template]["wall_ignore"] = tk.BooleanVar()
            wall_ignore = ttk.Checkbutton(
                master,
                text="Ignoruj poziom",
                variable=self.entries_content[template]["wall_ignore"],
                onvalue=True,
                offvalue=False,
            )
            wall_ignore.grid(row=5, column=0, pady=5, padx=(25, 5), sticky="W")

            ttk.Label(master, text="Min").grid(
                row=6, column=0, pady=5, padx=(25, 5), sticky="W"
            )

            self.entries_content[template]["min_wall"] = tk.IntVar()
            min_wall_level_input = ttk.Entry(
                master,
                width=5,
                textvariable=self.entries_content[template]["min_wall"],
                justify="center",
            )
            min_wall_level_input.grid(row=6, column=1, pady=5, padx=(5, 25), sticky="E")

            ttk.Label(master, text="Max").grid(
                row=7, column=0, pady=5, padx=(25, 5), sticky="W"
            )

            self.entries_content[template]["max_wall"] = tk.IntVar()
            max_wall_level_input = ttk.Entry(
                master,
                width=5,
                textvariable=self.entries_content[template]["max_wall"],
                justify="center",
            )
            max_wall_level_input.grid(row=7, column=1, pady=5, padx=(5, 25), sticky="E")

            # Wall ingore set command with partial func
            wall_ignore.configure(
                command=partial(
                    change_state,
                    [min_wall_level_input, max_wall_level_input],
                    "wall_ignore",
                    self.entries_content[template],
                ),
            )

            ttk.Label(master, text="Wysyłka ataków").grid(
                row=8, column=0, columnspan=2, pady=(20, 15), padx=5, sticky="W"
            )

            self.entries_content[template]["max_attacks"] = tk.BooleanVar()
            self.__setattr__(
                f"max_attacks_{template}",
                ttk.Checkbutton(
                    master,
                    text="Maksymalna ilość",
                    variable=self.entries_content[template]["max_attacks"],
                    onvalue=True,
                    offvalue=False,
                ),
            )
            max_attacks: ttk.Checkbutton = self.__getattribute__(
                f"max_attacks_{template}"
            )
            max_attacks.grid(row=9, column=0, pady=5, padx=(25, 5), sticky="W")

            ttk.Label(master, text="Ilość ataków").grid(
                row=10, column=0, pady=(5, 10), padx=(25, 5), sticky="W"
            )

            self.entries_content[template]["attacks_number"] = tk.IntVar()
            attacks_number_input = ttk.Entry(
                master,
                width=5,
                textvariable=self.entries_content[template]["attacks_number"],
                justify="center",
            )
            attacks_number_input.grid(
                row=10, column=1, pady=(5, 10), padx=(5, 25), sticky="E"
            )
            # Max attacks set command with partial func
            max_attacks.configure(
                command=partial(
                    change_state,
                    attacks_number_input,
                    "max_attacks",
                    self.entries_content[template],
                )
            )

            ttk.Label(master, text="Pozostałe ustawienia").grid(
                row=11, column=0, padx=5, pady=(20, 15), sticky="W"
            )

            ttk.Label(master, text="Powtarzaj ataki w odstępach [min]").grid(
                row=12, column=0, padx=(25, 5), pady=(0, 5), sticky="W"
            )

            if "farm_sleep_time" not in self.entries_content:
                self.entries_content["farm_sleep_time"] = tk.IntVar()
            farm_sleep_time = ttk.Entry(
                master,
                textvariable=self.entries_content["farm_sleep_time"],
                width=5,
                justify="center",
            )
            farm_sleep_time.grid(
                row=12, column=1, padx=(5, 25), pady=(0, 5), sticky="E"
            )

        farm_settings = ttk.Frame(templates)

        templates.add(farm_settings, text=f"Reguły wysyłki")

        self.scroll_able = ScrollableFrame(parent=farm_settings, show=True)
        farm_settings_scrolable = self.scroll_able.frame

        for template, row in zip(("A", "B", "C"), (1, 7, 13)):
            ttk.Label(farm_settings_scrolable, text=f"Szablon {template}").grid(
                row=row, padx=5, pady=16, sticky=tk.W
            )
            ttk.Label(farm_settings_scrolable, text=f"Wyślij wojsko gdy:").grid(
                row=row + 1, padx=25, pady=(0, 10), sticky=tk.W
            )
            farm_rules = self.entries_content[template]["farm_rules"] = {}
            farm_rules["loot"] = ttk.StringVar(value="mix_loot")
            max_loot = ttk.Radiobutton(
                farm_settings_scrolable,
                text="Ostatni atak wrócił z pełnym łupem",
                value="max_loot",
                variable=farm_rules["loot"],
            )
            max_loot.grid(row=row + 2, padx=45, pady=(5, 5), sticky=tk.W)
            min_loot = ttk.Radiobutton(
                farm_settings_scrolable,
                text="Ostatni atak wrócił z niepełnym łupem",
                value="min_loot",
                variable=farm_rules["loot"],
            )
            min_loot.grid(row=row + 3, padx=45, pady=5, sticky=tk.W)
            mix_loot = ttk.Radiobutton(
                farm_settings_scrolable,
                text="Wysyłaj bez względu na wielkość łupu",
                value="mix_loot",
                variable=farm_rules["loot"],
            )
            mix_loot.grid(row=row + 4, padx=45, pady=(5, 5), sticky=tk.W)

            tooltip_frame = ttk.Frame(farm_settings_scrolable)
            tooltip_frame.grid(
                row=row + 5, column=0, padx=(25, 0), pady=(10, 15), sticky=ttk.W
            )
            ttk.Label(
                tooltip_frame,
                text="Maksymalny czas przemarszu [min]",
            ).grid(row=0, column=0, sticky=ttk.W)
            info = ttk.Label(tooltip_frame, image=main_window.images.info)
            info.grid(row=0, column=1, padx=(5, 0))
            farm_rules["max_travel_time"] = ttk.IntVar()
            ToolTip(
                info,
                text="Określa maksymalny czas trwania przemarszu wojsk w jedną stronę.\n\n"
                "Wioska startowa -> wioska barbarzyńska.\n\n"
                "Wartość domyślna 0 oznacza brak limitu czasowego.",
                wraplength=350,
                topmost=True,
            )
            ttk.Entry(
                farm_settings_scrolable,
                textvariable=farm_rules["max_travel_time"],
                width=5,
                justify=ttk.CENTER,
            ).grid(row=row + 5, column=1, padx=(0, 25), pady=(10, 15), sticky=ttk.E)


class Scheduler(ScrollableFrame):
    """Content and functions to put in notebook frame f3 named 'Planer'."""

    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ) -> None:

        super().__init__(parent)
        self.entries_content = entries_content
        self.main_window = main_window

        entries_content["scheduler"] = {}

        ttk.Label(self.frame, text="Data wejścia wojsk").grid(
            row=2, column=0, columnspan=2, padx=5, pady=(15, 5), sticky=ttk.W
        )

        # Date entry settings
        date_frame = ttk.Frame(self.frame)
        date_frame.grid(row=3, column=0, columnspan=2, pady=(5, 0), sticky=ttk.EW)

        ttk.Label(date_frame, text="Od:").grid(row=0, column=0, pady=5, padx=(25, 5))
        ttk.Label(date_frame, text="Do:").grid(row=1, column=0, pady=5, padx=(25, 5))

        self.destiny_date = ttk.DateEntry(
            date_frame, dateformat="%d.%m.%Y %H:%M:%S:%f", firstweekday=0
        )
        self.destiny_date.grid(row=0, column=1, pady=5)
        self.date_entry = ttk.StringVar(value=self.destiny_date.entry.get())
        self.destiny_date.entry.configure(textvariable=self.date_entry)
        self.destiny_date.entry.configure(justify=ttk.CENTER)

        self.final_destiny_date = ttk.DateEntry(
            date_frame, dateformat="%d.%m.%Y %H:%M:%S:%f", firstweekday=0
        )
        self.final_destiny_date.grid(row=1, column=1, pady=5)
        self.final_date_entry = ttk.StringVar(value=self.destiny_date.entry.get())
        self.final_destiny_date.entry.configure(textvariable=self.final_date_entry)
        self.final_destiny_date.entry.configure(justify=ttk.CENTER)

        def date_entry_change() -> None:
            self.date_entry.trace_remove(*self.date_entry.trace_info()[0])

            def inner_call() -> None:
                self.date_entry.trace_remove(*self.date_entry.trace_info()[0])
                try:
                    destiny_date = datetime.strptime(
                        self.date_entry.get(), "%d.%m.%Y %H:%M:%S:%f"
                    ).timestamp()
                    final_destiny_date = datetime.strptime(
                        self.final_date_entry.get(), "%d.%m.%Y %H:%M:%S:%f"
                    ).timestamp()
                    if destiny_date > final_destiny_date:
                        self.final_date_entry.trace_remove(
                            *self.final_date_entry.trace_info()[0]
                        )
                        self.final_date_entry.set(self.date_entry.get())
                        self.final_date_entry.trace_add(
                            "write", lambda *_: final_date_entry_change()
                        )
                finally:
                    self.date_entry.trace_add("write", lambda *_: date_entry_change())
                    return

            self.date_entry.trace_add("write", lambda *_: inner_call())

        def final_date_entry_change() -> None:
            self.final_date_entry.trace_remove(*self.final_date_entry.trace_info()[0])

            def inner_call() -> None:
                self.final_date_entry.trace_remove(
                    *self.final_date_entry.trace_info()[0]
                )
                try:
                    destiny_date = datetime.strptime(
                        self.date_entry.get(), "%d.%m.%Y %H:%M:%S:%f"
                    ).timestamp()
                    final_destiny_date = datetime.strptime(
                        self.final_date_entry.get(), "%d.%m.%Y %H:%M:%S:%f"
                    ).timestamp()
                    if destiny_date > final_destiny_date:
                        self.date_entry.trace_remove(*self.date_entry.trace_info()[0])
                        self.date_entry.set(self.final_date_entry.get())
                        self.date_entry.trace_add(
                            "write", lambda *_: date_entry_change()
                        )
                finally:
                    self.final_date_entry.trace_add(
                        "write", lambda *_: final_date_entry_change()
                    )

            self.final_date_entry.trace_add("write", lambda *_: inner_call())

        self.date_entry.trace_add("write", lambda *_: date_entry_change())
        self.final_date_entry.trace_add("write", lambda *_: final_date_entry_change())

        # Text widgets
        ttk.Label(self.frame, text="Wioski startowe").grid(
            row=0, column=0, padx=5, pady=10
        )
        ttk.Label(self.frame, text="Wioski docelowe").grid(
            row=0, column=1, padx=5, pady=10
        )

        def clear_hint(text_widget: ttk.Text) -> None:
            if text_widget.get("1.0", "1.11") == "Współrzędne":
                text_widget.delete("1.0", "end")
                text_widget.unbind("<Button>")

        def text_hint(text_widget: ttk.Text) -> None:
            text_widget.insert(
                "1.0",
                "Współrzędne wiosek w formacie XXX|YYY "
                "oddzielone spacją, tabulatorem lub enterem.",
            )

        def text_mouse_scroll(text_widget: ttk.Text) -> None:
            def text_exceed(event=None) -> None:
                if text_widget.yview() != (0.0, 1.0):
                    self._unbound_to_mousewheel()
                    return
                self._bound_to_mousewheel()

            text_exceed()
            text_widget.bind("<Key>", lambda event: text_widget.after(25, text_exceed))
            text_widget.bind(
                "<<Paste>>", lambda event: text_widget.after(50, text_exceed), add="+"
            )

        def split_text(event=None) -> str | None:
            """Split to new rows if text is to long -> speedup tkinter Text widget"""

            clipboard_text: str = main_window.master.clipboard_get()
            if len(clipboard_text) > 200:
                splited_clipboard_text = clipboard_text.split()
                splited_clipboard_text = " ".join(
                    "\n" + text if not index % 20 and index else text
                    for index, text in enumerate(splited_clipboard_text)
                )
                main_window.master.clipboard_clear()
                main_window.master.clipboard_append(splited_clipboard_text + " ")
            else:
                main_window.master.clipboard_clear()
                main_window.master.clipboard_append(clipboard_text.strip() + " ")

        # Wioski startowe
        self.villages_to_use = tk.Text(self.frame, wrap="word", height=5, width=28)
        self.villages_to_use.grid(row=1, column=0, padx=5, pady=(0, 5), sticky=ttk.EW)
        self.villages_to_use.bind("<<Paste>>", split_text)
        self.villages_to_use.bind(
            "<Enter>", lambda event: text_mouse_scroll(self.villages_to_use)
        )
        self.villages_to_use.bind(
            "<Leave>", lambda event: self._bound_to_mousewheel(event)
        )
        self.villages_to_use.bind(
            "<Button>", lambda event: clear_hint(self.villages_to_use)
        )

        # Wioski docelowe
        self.villages_destiny = tk.Text(self.frame, wrap="word", height=5, width=28)
        self.villages_destiny.grid(row=1, column=1, padx=5, pady=(0, 5), sticky=ttk.EW)
        self.villages_destiny.bind("<<Paste>>", split_text)
        self.villages_destiny.bind(
            "<Enter>", lambda event: text_mouse_scroll(self.villages_destiny)
        )
        self.villages_destiny.bind(
            "<Leave>", lambda event: self._bound_to_mousewheel(event)
        )
        self.villages_destiny.bind(
            "<Button>", lambda event: clear_hint(self.villages_destiny)
        )

        text_hint(self.villages_to_use)
        text_hint(self.villages_destiny)

        # Rodzaj komendy -> atak lub wsparcie
        ttk.Label(self.frame, text="Rodzaj komendy").grid(
            row=5, column=0, columnspan=2, padx=5, pady=(10, 5), sticky=tk.W
        )
        self.command_type = tk.StringVar()
        self.command_type_attack = ttk.Radiobutton(
            self.frame,
            text="Atak",
            value="target_attack",
            variable=self.command_type,
        )
        self.command_type_attack.grid(
            row=6, column=0, padx=(25, 5), pady=5, sticky=tk.W
        )
        self.command_type_support = ttk.Radiobutton(
            self.frame,
            text="Wsparcie",
            value="target_support",
            variable=self.command_type,
        )
        self.command_type_support.grid(
            row=7, column=0, padx=(25, 5), pady=5, sticky=tk.W
        )

        # Szablon wojsk
        ttk.Label(self.frame, text="Szablon wojsk").grid(
            row=8, column=0, padx=5, pady=(10, 5), sticky=tk.W
        )

        # Wyślij wszystkie
        # region

        self.template_type = tk.StringVar()

        def disable_or_enable_entry_state(var, index, mode):
            enable = False
            if self.template_type.get() == "send_my_template":
                enable = True
            for child in (
                army_frame.winfo_children() + attacks_number_frame.winfo_children()
            ):
                wtype = child.winfo_class()
                if wtype == "TEntry":
                    if enable:
                        child.config(state="normal")
                    else:
                        child.config(state="disabled")

        self.template_type.trace_add("write", disable_or_enable_entry_state)
        self.all_troops_radiobutton = ttk.Radiobutton(
            self.frame,
            text="Wyślij wszystkie",
            value="send_all",
            variable=self.template_type,
            command=lambda: [
                self.choosed_fake_template.set(""),
                self.choose_slowest_troop.config(state="readonly"),
                self.choose_catapult_target.config(state="readonly"),
                self.choose_catapult_target.set("Default"),
                self.repeat_attack.set(False),
                self.total_attacks_number_entry.config(state="disabled"),
                forget_row(self.frame, row_number=43),
            ],
        )
        self.all_troops_radiobutton.grid(
            row=9, column=0, columnspan=2, padx=(25, 5), pady=5, sticky=tk.W
        )

        self.army_type = tk.StringVar()  # Wysłać jednostki off czy deff
        self.only_off_radiobutton = ttk.Radiobutton(
            self.frame,
            text="Wyślij tylko jednostki offensywne",
            value="only_off",
            variable=self.army_type,
            command=lambda: self.all_troops_radiobutton.invoke(),
        )
        self.only_off_radiobutton.grid(
            row=14, column=0, columnspan=2, padx=(45, 5), pady=5, sticky=tk.W
        )

        self.only_deff_radiobutton = ttk.Radiobutton(
            self.frame,
            text="Wyślij tylko jednostki deffensywne",
            value="only_deff",
            variable=self.army_type,
            command=lambda: self.all_troops_radiobutton.invoke(),
        )
        self.only_deff_radiobutton.grid(
            row=15, column=0, columnspan=2, padx=(45, 5), pady=5, sticky=tk.W
        )

        self.send_snob = tk.StringVar()  # Czy wysłać szlachtę
        self.no_snob_radiobutton = ttk.Radiobutton(
            self.frame,
            text="Nie wysyłaj szlachty",
            value="no_snob",
            variable=self.send_snob,
            command=lambda: [
                self.all_troops_radiobutton.invoke(),
                self.snob_amount_entry.config(state="disabled"),
                self.first_snob_army_size_entry.config(state="disabled"),
                self.slowest_troop.set("Taran"),
            ],
        )
        self.no_snob_radiobutton.grid(
            row=10, column=0, columnspan=2, padx=(45, 5), pady=5, sticky=tk.W
        )

        self.send_snob_radiobutton = ttk.Radiobutton(
            self.frame,
            text="Wyślij szlachtę",
            value="send_snob",
            variable=self.send_snob,
            command=lambda: [
                self.all_troops_radiobutton.invoke(),
                self.snob_amount_entry.config(state="normal"),
                self.first_snob_army_size_entry.config(state="normal"),
                self.slowest_troop.set("Szlachcic"),
            ],
        )
        self.send_snob_radiobutton.grid(
            row=11, column=0, columnspan=2, padx=(45, 5), pady=5, sticky=tk.W
        )

        ttk.Label(self.frame, text="Liczba szlachiców").grid(
            row=12, column=0, columnspan=2, padx=(65, 5), pady=(5, 0), sticky=tk.W
        )
        self.snob_amount = tk.IntVar()  # Ile grubych wysłać
        self.snob_amount_entry = ttk.Entry(
            self.frame,
            textvariable=self.snob_amount,
            width=4,
            justify=tk.CENTER,
            state="disabled",
        )
        self.snob_amount_entry.grid(
            row=12, column=0, columnspan=2, padx=(5, 25), pady=(5, 0), sticky=tk.E
        )

        ttk.Label(self.frame, text="Obstawa pierwszego szlachcica [%]").grid(
            row=13, column=0, columnspan=2, padx=(65, 5), pady=5, sticky=tk.W
        )
        self.first_snob_army_size = (
            tk.IntVar()
        )  # Wielkość obstawy pierwszego grubego wyrażona w %
        self.first_snob_army_size_entry = ttk.Entry(
            self.frame,
            textvariable=self.first_snob_army_size,
            width=4,
            justify=tk.CENTER,
            state="disabled",
        )
        self.first_snob_army_size_entry.grid(
            row=13, column=0, columnspan=2, padx=(5, 25), pady=5, sticky=tk.E
        )

        ttk.Label(self.frame, text="Najwolniejsza jednostka").grid(
            row=16, column=0, columnspan=2, padx=(45, 5), pady=(10, 5), sticky=tk.W
        )
        self.slowest_troop = tk.StringVar()
        self.choose_slowest_troop = ttk.Combobox(
            self.frame,
            textvariable=self.slowest_troop,
            width=14,
            justify=tk.CENTER,
            state="disabled",
        )
        self.choose_slowest_troop.grid(
            row=16, column=0, columnspan=2, padx=(5, 25), pady=(10, 5), sticky=tk.E
        )
        self.choose_slowest_troop["values"] = (
            "Pikinier",
            "Miecznik",
            "Topornik",
            "Łucznik",
            "Zwiadowca",
            "Lekka kawaleria",
            "Łucznik konny",
            "Ciężka kawaleria",
            "Taran",
            "Katapulta",
            "Rycerz",
            "Szlachcic",
        )

        ttk.Label(self.frame, text="Cel ostrzału katapultami").grid(
            row=17, column=0, columnspan=2, padx=(45, 5), pady=(5, 10), sticky=tk.W
        )
        self.catapult_target = tk.StringVar()
        self.choose_catapult_target = ttk.Combobox(
            self.frame,
            textvariable=self.catapult_target,
            values=["Default"] + list(main_window.buildings),
            width=14,
            justify=tk.CENTER,
            state="disabled",
        )
        self.choose_catapult_target.grid(
            row=17, column=0, columnspan=2, padx=(5, 25), pady=(5, 10), sticky=tk.E
        )
        # endregion

        # Wyślij fejki
        # region
        self.fake_troops_radiobutton = ttk.Radiobutton(
            self.frame,
            text="Wyślij fejki",
            value="send_fake",
            variable=self.template_type,
            command=lambda: [
                self.send_snob.set(""),
                self.snob_amount_entry.config(state="disabled"),
                self.first_snob_army_size_entry.config(state="disabled"),
                self.army_type.set(""),
                self.slowest_troop.set(""),
                self.choose_slowest_troop.config(state="disabled"),
                self.repeat_attack.set(False),
                self.total_attacks_number_entry.config(state="disabled"),
                self.choose_catapult_target.config(state="disabled"),
                forget_row(self.frame, row_number=43),
            ],
        )
        self.fake_troops_radiobutton.grid(
            row=18, column=0, columnspan=2, padx=(25, 5), pady=5, sticky=tk.W
        )

        ttk.Label(self.frame, text="Dostępne szablony").grid(
            row=19, column=0, columnspan=2, padx=(45, 5), pady=5, sticky=tk.W
        )

        settings.setdefault("scheduler", {})
        settings["scheduler"].setdefault("fake_templates", {})
        self.choosed_fake_template = tk.StringVar()  # Wybrany szablon
        self.available_templates(
            settings=settings
        )  # Wyświetla dostępne szablony stworzone przez użytkownika

        ttk.Button(
            self.frame,
            image=main_window.images.plus,
            bootstyle="primary.Link.TButton",
            command=lambda: self.create_template(settings=settings),
        ).grid(row=19, column=0, columnspan=2, padx=(0, 27), pady=5, sticky=tk.E)

        button_info_frame = ttk.Frame(self.frame)
        button_info_frame.grid(
            row=41, column=0, columnspan=2, padx=(25, 5), pady=10, sticky=tk.W
        )
        # endregion

        # Własny szablon
        # region

        def on_catapult_value_change(*args) -> None:
            if (
                not self.choose_catapult_target2.winfo_ismapped()
                and self.troops["catapult"].get()
            ):
                ttk.Label(self.frame, text="Cel ostrzału katapultami").grid(
                    row=43,
                    column=0,
                    columnspan=2,
                    padx=(45, 5),
                    pady=(15, 0),
                    sticky=tk.W,
                )
                self.choose_catapult_target2.grid(
                    row=43,
                    column=0,
                    columnspan=2,
                    padx=(5, 25),
                    pady=(15, 0),
                    sticky=tk.E,
                )
                return
            if (
                self.choose_catapult_target2.winfo_ismapped()
                and not self.troops["catapult"].get()
            ):
                forget_row(self.frame, row_number=43)

        def own_template_radiobutton_func() -> None:
            """self.own_template_radiobutton function"""

            self.send_snob.set(""),
            self.snob_amount_entry.config(state="disabled"),
            self.first_snob_army_size_entry.config(state="disabled"),
            self.army_type.set(""),
            self.slowest_troop.set(""),
            self.choosed_fake_template.set(""),
            self.choose_slowest_troop.config(state="disabled")
            self.split_attacks_number.set("1")
            self.choose_catapult_target.config(state="disabled")
            on_catapult_value_change()

        self.own_template_radiobutton = ttk.Radiobutton(
            button_info_frame,
            text="Własny szablon",
            value="send_my_template",
            variable=self.template_type,
            command=own_template_radiobutton_func,
        )
        self.own_template_radiobutton.grid(row=0, column=0, sticky=tk.W)

        info = ttk.Label(button_info_frame, image=main_window.images.info)
        info.grid(row=0, column=1, padx=(5, 0), sticky=ttk.W)

        ToolTip(
            info,
            text="W poniższych polach można podać konkretną liczbę jednostek do wysłania lub wpisać słowo max. "
            "Słowo max oznacza wybranie maksymalnej ilości danej jednostki dostępnej w wiosce w chwili wysyłania "
            "ataku/wsparcia.\n\nDla ułatwienia można kliknąć w ikonę jednostki co w przypadku pustej komórki "
            "doda wartość max a w pozostałych przypadkach wyczyści ją.",
            wraplength=350,
            topmost=True,
        )

        army_frame = ttk.Frame(self.frame)
        army_frame.grid(row=42, column=0, columnspan=2, sticky=tk.EW)

        army_frame.columnconfigure(0, weight=11)
        army_frame.columnconfigure(1, weight=11)
        army_frame.columnconfigure(2, weight=10)
        army_frame.columnconfigure(3, weight=10)

        def clear_or_set_max(label: ttk.Label, troop_entry: tk.StringVar):
            if self.template_type.get() != "send_my_template":
                self.own_template_radiobutton.invoke()
            if troop_entry.get().strip():
                troop_entry.set("")
            else:
                troop_entry.set("max")

        spear_label = ttk.Label(
            army_frame,
            image=main_window.images.spear,
        )
        spear_label.grid(row=0, column=0, padx=(25, 0), pady=(5, 0), sticky=tk.W)
        spear_label.bind(
            "<Button-1>", lambda _: clear_or_set_max(spear_label, self.troops["spear"])
        )

        spy_label = ttk.Label(army_frame, image=main_window.images.spy)
        spy_label.grid(row=0, column=1, padx=(25, 0), pady=(5, 0), sticky=tk.W)
        spy_label.bind(
            "<Button-1>", lambda _: clear_or_set_max(spy_label, self.troops["spy"])
        )

        ram_label = ttk.Label(army_frame, image=main_window.images.ram)
        ram_label.grid(row=0, column=2, padx=(21, 0), pady=(5, 0), sticky=tk.W)
        ram_label.bind(
            "<Button-1>", lambda _: clear_or_set_max(ram_label, self.troops["ram"])
        )

        knihgt_label = ttk.Label(army_frame, image=main_window.images.knight)
        knihgt_label.grid(row=0, column=3, padx=(21, 0), pady=(5, 0), sticky=tk.W)
        knihgt_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(knihgt_label, self.troops["knight"]),
        )

        sword_label = ttk.Label(army_frame, image=main_window.images.sword)
        sword_label.grid(row=1, column=0, padx=(25, 0), pady=(5, 0), sticky=tk.W)
        sword_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(sword_label, self.troops["sword"]),
        )

        light_label = ttk.Label(army_frame, image=main_window.images.light)
        light_label.grid(row=1, column=1, padx=(25, 0), pady=(5, 0), sticky=tk.W)
        light_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(light_label, self.troops["light"]),
        )

        catapult_label = ttk.Label(army_frame, image=main_window.images.catapult)
        catapult_label.grid(row=1, column=2, padx=(21, 0), pady=(5, 0), sticky=tk.W)
        catapult_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(catapult_label, self.troops["catapult"]),
        )

        snob_label = ttk.Label(army_frame, image=main_window.images.snob)
        snob_label.grid(row=1, column=3, padx=(21, 0), pady=(5, 0), sticky=tk.W)
        snob_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(snob_label, self.troops["snob"]),
        )

        axe_label = ttk.Label(army_frame, image=main_window.images.axe)
        axe_label.grid(row=2, column=0, padx=(25, 0), pady=(5, 0), sticky=tk.W)
        axe_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(axe_label, self.troops["axe"]),
        )

        marcher_label = ttk.Label(army_frame, image=main_window.images.marcher)
        marcher_label.grid(row=2, column=1, padx=(25, 0), pady=(5, 0), sticky=tk.W)
        marcher_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(marcher_label, self.troops["marcher"]),
        )

        archer_label = ttk.Label(army_frame, image=main_window.images.archer)
        archer_label.grid(row=3, column=0, padx=(25, 0), pady=(5, 5), sticky=tk.W)
        archer_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(archer_label, self.troops["archer"]),
        )

        heavy_label = ttk.Label(army_frame, image=main_window.images.heavy)
        heavy_label.grid(row=3, column=1, padx=(25, 0), pady=(5, 5), sticky=tk.W)
        heavy_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(heavy_label, self.troops["heavy"]),
        )

        self.troops = {
            "spear": tk.StringVar(),
            "sword": tk.StringVar(),
            "axe": tk.StringVar(),
            "archer": tk.StringVar(),
            "spy": tk.StringVar(),
            "light": tk.StringVar(),
            "marcher": tk.StringVar(),
            "heavy": tk.StringVar(),
            "ram": tk.StringVar(),
            "catapult": tk.StringVar(),
            "knight": tk.StringVar(),
            "snob": tk.StringVar(),
        }

        self.troops["catapult"].trace_add("write", on_catapult_value_change)

        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["spear"],
        ).grid(row=0, column=0, padx=(0, 0), pady=(5, 0), sticky=tk.E)
        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["spy"],
        ).grid(row=0, column=1, padx=(0, 3), pady=(5, 0), sticky=tk.E)
        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["ram"],
        ).grid(row=0, column=2, padx=(0, 0), pady=(5, 0), sticky=tk.E)
        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["knight"],
        ).grid(row=0, column=3, padx=(0, 25), pady=(5, 0), sticky=tk.E)
        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["sword"],
        ).grid(row=1, column=0, padx=(0, 0), pady=(5, 0), sticky=tk.E)
        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["light"],
        ).grid(row=1, column=1, padx=(0, 3), pady=(5, 0), sticky=tk.E)
        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["catapult"],
        ).grid(row=1, column=2, padx=(0, 0), pady=(5, 0), sticky=tk.E)
        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["snob"],
        ).grid(row=1, column=3, padx=(0, 25), pady=(5, 0), sticky=tk.E)
        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["axe"],
        ).grid(row=2, column=0, padx=(0, 0), pady=(5, 0), sticky=tk.E)
        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["marcher"],
        ).grid(row=2, column=1, padx=(0, 3), pady=(5, 0), sticky=tk.E)
        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["archer"],
        ).grid(row=3, column=0, padx=(0, 0), pady=(5, 5), sticky=tk.E)
        ttk.Entry(
            army_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.troops["heavy"],
        ).grid(row=3, column=1, padx=(0, 3), pady=(5, 5), sticky=tk.E)

        self.choose_catapult_target2 = ttk.Combobox(
            self.frame,
            textvariable=self.catapult_target,
            values=["Default"] + list(main_window.buildings),
            state="readonly",
            width=14,
            justify=tk.CENTER,
        )

        # Liczba ataków
        attacks_number_frame = ttk.Labelframe(
            army_frame, text="Liczba ataków", labelanchor="n"
        )
        attacks_number_frame.grid(
            row=2,
            rowspan=2,
            column=2,
            columnspan=2,
            padx=(25, 25),
            pady=(5, 5),
            sticky=tk.NSEW,
        )
        attacks_number_frame.rowconfigure(0, weight=1)
        attacks_number_frame.columnconfigure(0, weight=1)
        self.split_attacks_number = ttk.IntVar()
        ttk.Entry(
            attacks_number_frame,
            width=5,
            state="disabled",
            justify=tk.CENTER,
            textvariable=self.split_attacks_number,
        ).grid(row=0, column=0)

        settings["scheduler"].setdefault("ready_schedule", [])
        if settings["scheduler"]["ready_schedule"]:
            current_time = time.time()
            settings["scheduler"]["ready_schedule"] = [
                value
                for value in settings["scheduler"]["ready_schedule"]
                if value["send_time"] > current_time
            ]

        self.repeat_attack = tk.BooleanVar()

        def repeat_attack_checkbutton_command() -> None:
            if self.repeat_attack.get():
                if not parent.winfo_viewable():
                    return
                split_attacks_number = self.split_attacks_number.get()
                self.own_template_radiobutton.invoke()
                self.split_attacks_number.set(split_attacks_number)
                self.total_attacks_number_entry.config(state="normal")
            else:
                self.total_attacks_number_entry.config(state="disabled")

        self.repeat_attack_checkbutton = ttk.Checkbutton(
            self.frame,
            text="Powtórz atak po powrocie jednostek",
            variable=self.repeat_attack,
            onvalue=True,
            offvalue=False,
            command=repeat_attack_checkbutton_command,
        )
        self.repeat_attack_checkbutton.grid(
            row=44, columnspan=2, padx=(45, 0), pady=(20, 0), sticky=tk.W
        )

        self.total_attacks_number = tk.IntVar()
        self.total_attacks_number_label = ttk.Label(
            self.frame, text="Łączna liczba ataków"
        )
        self.total_attacks_number_label.grid(
            row=45, column=0, padx=(65, 0), pady=10, sticky=tk.W
        )
        self.total_attacks_number_entry = ttk.Entry(
            self.frame,
            textvariable=self.total_attacks_number,
            width=4,
            justify=tk.CENTER,
            state="disabled",
        )
        self.total_attacks_number_entry.grid(
            row=45, columnspan=2, padx=(5, 25), pady=10, sticky=tk.E
        )

        # endregion

        ttk.Separator(self.frame, orient="horizontal").grid(
            row=46, column=0, columnspan=2, pady=(5, 0), sticky=("W", "E")
        )

        self.show_schedule = ttk.Button(
            self.frame,
            text="Pokaż planer [F4]",
            command=lambda: self.show_existing_schedule(
                settings=settings, main_window=main_window
            ),
        )
        self.show_schedule.grid(
            row=47, column=0, padx=(25, 12.5), pady=10, sticky=ttk.EW
        )

        self.add_to_schedule = ttk.Button(
            self.frame,
            text="Dodaj do planera [F5]",
            command=lambda: self.create_schedule(
                settings=settings, main_window=main_window
            ),
        )
        self.add_to_schedule.grid(
            row=47, column=1, padx=(12.5, 25), pady=10, sticky=ttk.EW
        )

        # Bindings

        self.frame.bind_all("<F4>", lambda _: self.show_schedule.invoke())
        self.frame.bind_all("<F5>", lambda _: self.add_to_schedule.invoke())

    def available_templates(self, settings: dict) -> None:
        def delete_template(row_number, fake_templates, template_name):
            del fake_templates[template_name]
            forget_row(self.frame, row_number)
            self.frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        fake_templates = settings["scheduler"]["fake_templates"]

        if not fake_templates:
            ttk.Label(self.frame, text="Brak dostępnych szablonów").grid(
                row=20, column=0, columnspan=2, padx=(65, 5), pady=(0, 5), sticky=tk.W
            )

        for index, template_name in enumerate(fake_templates):
            template_button = ttk.Radiobutton(
                self.frame,
                text=f"{template_name}",
                value=fake_templates[template_name],
                variable=self.choosed_fake_template,
                command=lambda: self.fake_troops_radiobutton.invoke(),
            )
            template_button.grid(
                row=20 + index, column=0, columnspan=2, padx=(65, 5), sticky=tk.W
            )
            text = "\n".join(
                f'{troop["priority_number"]} {troop_name.upper()}  Min={troop["min_value"]}  Max={troop["max_value"]}'
                for troop_name, troop in fake_templates[
                    list(fake_templates)[index]
                ].items()
            )
            ToolTip(template_button, text=text, topmost=True)
            ttk.Button(
                self.frame,
                image=self.main_window.images.exit,
                bootstyle="primary.Link.TButton",
                command=partial(
                    delete_template, index + 20, fake_templates, template_name
                ),
            ).grid(row=20 + index, column=0, columnspan=2, padx=(5, 27), sticky=tk.E)

    @log_errors()
    def create_schedule(self, settings: dict, main_window: "MainWindow") -> None:
        """Create scheduled defined on used options by the user"""

        def local_custom_error(message, scroll_to_top: bool = True) -> None:
            custom_error(message=message, parent=self.canvas)
            if scroll_to_top:
                self.canvas.yview_moveto(0)

        # Safeguards
        if self.villages_to_use.get(
            "1.0", "1.5"
        ) == "Współ" or self.villages_to_use.compare("end-1c", "==", "1.0"):
            local_custom_error("Brak wiosek startowych")
            return
        if self.villages_destiny.get(
            "1.0", "1.5"
        ) == "Współ" or self.villages_destiny.compare("end-1c", "==", "1.0"):
            local_custom_error("Brak wiosek docelowych")
            return
        if not self.command_type.get():
            local_custom_error("Wybierz rodzaj komendy")
            return
        if (
            "send_fake" in self.template_type.get()
            and not self.choosed_fake_template.get()
        ):
            local_custom_error("Wybierz szablon fejków do wysłania", False)
            return
        if "" in self.template_type.get() and not self.repeat_attack.get():
            local_custom_error("Liczba ataków powinna być większa od 0", False)
            return

        # Base info
        sends_from = self.villages_to_use.get("1.0", tk.END)
        sends_to = self.villages_destiny.get("1.0", tk.END)
        command_type = self.command_type.get()
        template_type = self.template_type.get()

        # Timings
        arrival_time = self.destiny_date.entry.get()
        arrival_time_in_sec = datetime.strptime(
            arrival_time, "%d.%m.%Y %H:%M:%S:%f"
        ).timestamp()
        final_arrival_time = self.final_destiny_date.entry.get()
        final_arrival_time_in_sec = datetime.strptime(
            final_arrival_time, "%d.%m.%Y %H:%M:%S:%f"
        ).timestamp()
        set_low_priority = False
        current_time = time.time()
        timings_ommiting_night_bonus: list[tuple[float, float]] = []
        if arrival_time != final_arrival_time:

            class Night(NamedTuple):
                start_hour: int = int(settings["world_config"]["start_hour"])
                end_hour: int = int(settings["world_config"]["end_hour"])

            night = Night()

            start = datetime.strptime(arrival_time[:10], f"%d.%m.%Y")
            end = datetime.strptime(final_arrival_time[:10], f"%d.%m.%Y")

            first_night_bonus_start = datetime.strptime(
                f"{arrival_time[:10]} {night.start_hour}:00:00:000",
                f"%d.%m.%Y %H:%M:%S:%f",
            ).timestamp()
            # Same day
            if not (end - start).days:
                timings_ommiting_night_bonus.append(
                    (
                        arrival_time_in_sec,
                        final_arrival_time_in_sec - arrival_time_in_sec
                        if final_arrival_time_in_sec < first_night_bonus_start
                        else first_night_bonus_start - arrival_time_in_sec,
                    )
                )
            # Diffrent days
            else:
                last_night_bonus_end = datetime.strptime(
                    f"{final_arrival_time[:10]} {night.end_hour}:00:00:000",
                    f"%d.%m.%Y %H:%M:%S:%f",
                ).timestamp()
                # When night.start == 0 than skip to the begining of the next day
                if not night.start_hour:
                    first_night_bonus_start += timedelta(days=1).total_seconds()
                    day_duration = (24 - night.end_hour) * 3600
                else:
                    day_duration = (night.start_hour - night.end_hour) * 3600
                # Compute timings for first day
                time_to_night = first_night_bonus_start - arrival_time_in_sec
                timings_ommiting_night_bonus.append(
                    (arrival_time_in_sec, time_to_night)
                )
                # Compute timings for every other day between first and last
                if (end - start).days > 1:
                    for day in range(1, (end - start).days):
                        timings_ommiting_night_bonus.append(
                            (
                                (
                                    start + timedelta(days=day, hours=night.end_hour)
                                ).timestamp(),
                                day_duration,
                            )
                        )
                # Compute timings for last day and ommit it if it's at night bonus
                if final_arrival_time_in_sec > last_night_bonus_end:
                    if final_arrival_time_in_sec < last_night_bonus_end + day_duration:
                        time_to_night = final_arrival_time_in_sec - last_night_bonus_end
                    else:
                        time_to_night = day_duration
                    timings_ommiting_night_bonus.append(
                        (last_night_bonus_end, time_to_night)
                    )

        if final_arrival_time_in_sec - arrival_time_in_sec > 299:
            set_low_priority = True

        troops_speed = {
            "spear": 18,
            "sword": 22,
            "axe": 18,
            "archer": 18,
            "spy": 9,
            "light": 10,
            "marcher": 10,
            "heavy": 11,
            "ram": 30,
            "catapult": 30,
            "knight": 10,
            "snob": 35,
        }

        match template_type:
            case "send_all":
                army_type = self.army_type.get()
                send_snob = self.send_snob.get()
                if send_snob == "send_snob":
                    snob_amount = self.snob_amount.get()
                    first_snob_army_size = self.first_snob_army_size.get()
                catapult_target = self.catapult_target.get()
                if catapult_target != "Default":
                    for key, value in zip(
                        main_window.buildings._fields, main_window.buildings
                    ):
                        if value == catapult_target:
                            catapult_target = key

            case "send_fake":
                choosed_fake_template = json.loads(
                    self.choosed_fake_template.get().replace("'", '"')
                )
                sorted_choosed_fake_template = sorted(
                    choosed_fake_template.items(),
                    key=lambda x: x[1]["priority_number"],
                )
                army_speed = max(
                    troops_speed[troop_name]
                    for troop_name, dict_info in sorted_choosed_fake_template
                    if dict_info["min_value"] > 0
                )

            case "send_my_template":
                troops = {}
                for troop_name, troop_value in self.troops.items():
                    troop_value = troop_value.get().strip()
                    if troop_value:
                        troops[troop_name] = troop_value
                army_speed = max(
                    troops_speed[troop_name] for troop_name in troops.keys()
                )
                if (
                    command_type == "target_support"
                    and "knight" in troops
                    and (troops["knight"] == "max" or int(troops["knight"]) > 0)
                ):
                    army_speed = 10
                split_attacks_number = self.split_attacks_number.get() or "1"
                catapult_target = self.catapult_target.get()
                if catapult_target != "Default":
                    for key, value in zip(
                        main_window.buildings._fields, main_window.buildings
                    ):
                        if value == catapult_target:
                            catapult_target = key
                repeat_attack = self.repeat_attack.get()
                total_attacks_number = self.total_attacks_number.get()

        villages = app_functions.get_villages_id(settings=settings)

        send_info_list = []  # When, from where, attack or help, amount of troops etc.
        sends_from = sends_from.split()
        sends_to = sends_to.split()
        for send_from, send_to in zip(sends_from, sends_to):
            send_info = {}
            send_info["send_from"] = send_from
            send_info["send_to"] = send_to
            send_info["command"] = command_type  # Is it attack or help
            send_info[
                "template_type"
            ] = template_type  # send_all/send_fake/send_my_template

            try:
                send_from_village_id = villages[send_from][:-1]  # It returns village ID
                send_to_village_id = villages[send_to][:-1]  # It returns village ID
            except KeyError:
                villages = app_functions.get_villages_id(
                    settings=settings, update=True
                )  # Update villages
                try:
                    send_from_village_id = villages[send_from][
                        :-1
                    ]  # It returns village ID
                except KeyError:
                    custom_error(
                        message=f"Wioska {send_from} nie istnieje.",
                        parent=main_window.master,
                    )
                    self.canvas.yview_moveto(0)
                    return
                try:
                    send_to_village_id = villages[send_to][:-1]  # It returns village ID
                except KeyError:
                    custom_error(
                        message=f"Wioska {send_to} nie istnieje.",
                        parent=main_window.master,
                    )
                    self.canvas.yview_moveto(0)
                    return

            send_info["url"] = (
                f"https://"
                f'{settings["server_world"]}'
                f".{settings['game_url']}/game.php?village="
                f"{send_from_village_id}"
                f"&screen=place&target="
                f"{send_to_village_id}"
            )

            match template_type:

                case "send_all":
                    send_info["army_type"] = army_type
                    send_info["send_snob"] = send_snob
                    if send_snob == "send_snob":
                        send_info["snob_amount"] = snob_amount
                        send_info["first_snob_army_size"] = first_snob_army_size

                    troops_dictionary = {
                        "Pikinier": "spear",
                        "Miecznik": "sword",
                        "Topornik": "axe",
                        "Łucznik": "archer",
                        "Zwiadowca": "spy",
                        "Lekka kawaleria": "light",
                        "Łucznik konny": "marcher",
                        "Ciężka kawaleria": "heavy",
                        "Taran": "ram",
                        "Katapulta": "catapult",
                        "Rycerz": "knight",
                        "Szlachcic": "snob",
                    }
                    slowest_troop = self.slowest_troop.get()
                    slowest_troop = troops_dictionary[slowest_troop]
                    send_info["slowest_troop"] = slowest_troop
                    army_speed = troops_speed[slowest_troop]
                    send_info["catapult_target"] = catapult_target

                case "send_fake":
                    send_info["fake_template"] = choosed_fake_template

                case "send_my_template":
                    send_info["troops"] = troops
                    send_info["split_attacks_number"] = split_attacks_number
                    if "catapult" in troops:
                        send_info["catapult_target"] = catapult_target
                    send_info["repeat_attack"] = repeat_attack
                    send_info["total_attacks_number"] = total_attacks_number

            distance = sqrt(
                pow(int(send_from[:3]) - int(send_to[:3]), 2)
                + pow(int(send_from[4:]) - int(send_to[4:]), 2)
            )
            travel_time_in_sec = round(
                army_speed * distance * 60
            )  # Milisekundy są zaokrąglane do pełnych sekund
            send_info["travel_time"] = travel_time_in_sec

            if timings_ommiting_night_bonus:
                drawn_arrival_time, max_time_to_add = random.choice(
                    timings_ommiting_night_bonus
                )
                drawn_extra_time = random.uniform(0, max_time_to_add)
                current_command_final_arrival_time_in_sec = (
                    drawn_arrival_time + drawn_extra_time
                )
                send_info["arrival_time"] = datetime.strftime(
                    datetime.fromtimestamp(current_command_final_arrival_time_in_sec),
                    "%d.%m.%Y %H:%M:%S:%f",
                )[:-3]
                send_info["send_time"] = (
                    current_command_final_arrival_time_in_sec - travel_time_in_sec
                )  # sec since epoch
                if set_low_priority:
                    send_info["low_priority"] = True
                    if drawn_extra_time < 8:
                        send_info["send_time"] += 8
                    elif drawn_extra_time + 8 > max_time_to_add:
                        send_info["send_time"] += 5

            else:
                send_info["arrival_time"] = arrival_time
                send_info["send_time"] = (
                    arrival_time_in_sec - travel_time_in_sec
                )  # sec since epoch

            if send_info["send_time"] - 3 < current_time:
                sends_from.append(send_from)
                continue

            send_info_list.append(send_info)

        if not send_info_list:
            custom_error(
                message="Termin wysyłki wojsk już minął", parent=main_window.master
            )
            self.canvas.yview_moveto(0)
            return

        # Changed to settings["scheduler"]["ready_schedule"] also changes
        # settings_by_worlds[server_world]["scheduler"]["ready_schedule"]
        if hasattr(main_window, "to_do"):
            server_world = settings["server_world"]
            for cell in send_info_list:
                settings["scheduler"]["ready_schedule"].append(cell)
                main_window.to_do.append(
                    {
                        "func": "send_troops",
                        "start_time": cell["send_time"] - 8,
                        "server_world": server_world,
                        "settings": main_window.settings_by_worlds[server_world],
                        "errors_number": 0,
                    }
                )
        else:
            for cell in send_info_list:
                settings["scheduler"]["ready_schedule"].append(cell)
        # Sort to_do if running and currently not busy
        if main_window.running:
            _time = main_window.time.get()
            if _time != "Running..":
                h, min, sec = (int(_) for _ in _time.split(":"))
                total_sec = h * 3600 + min * 60 + sec
                if total_sec > 1:
                    main_window.to_do.sort(key=lambda sort_by: sort_by["start_time"])
        settings["scheduler"]["ready_schedule"].sort(key=lambda x: x["send_time"])

        # Scroll-up the page and clear input fields
        self.canvas.yview_moveto(0)
        self.villages_to_use.delete("1.0", tk.END)
        self.villages_destiny.delete("1.0", tk.END)

        custom_error(
            message="Dodano do planera!", auto_hide=True, parent=main_window.master
        )

    @log_errors()
    def create_template(self, settings: dict) -> None:
        """As named it creates fake template to use"""

        def add_to_template() -> None:

            nonlocal last_row_number, template

            def _forget_row(row_number, troop_name) -> None:
                forget_row(frame, row_number)
                del template[troop_name]

            priority = priority_number.get()
            troop = troop_type.get()
            min = min_value.get()
            max = max_value.get()

            ttk.Label(frame, text=f"{priority}").grid(row=last_row_number, column=0)

            ttk.Label(frame, text=f"{troop}").grid(row=last_row_number, column=1)

            ttk.Label(frame, text=f"{min}").grid(row=last_row_number, column=2)

            ttk.Label(frame, text=f"{max}").grid(row=last_row_number, column=3)

            troop_dictionary = {
                "Pikinier": "spear",
                "Miecznik": "sword",
                "Topornik": "axe",
                "Łucznik": "archer",
                "Zwiadowca": "spy",
                "Lekka kawaleria": "light",
                "Łucznik konny": "marcher",
                "Ciężka kawaleria": "heavy",
                "Taran": "ram",
                "Katapulta": "catapult",
            }

            troop = troop_dictionary[troop]

            match troop:
                case "spear" | "sword" | "axe" | "archer":
                    troop_population = 1
                case "spy":
                    troop_population = 2
                case "light":
                    troop_population = 4
                case "marcher" | "ram":
                    troop_population = 5
                case "heavy":
                    troop_population = 6
                case "catapult":
                    troop_population = 8

            ttk.Button(
                frame,
                image=self.main_window.images.minimize,
                bootstyle="primary.Link.TButton",
                command=partial(_forget_row, last_row_number, troop),
            ).grid(row=last_row_number, column=4, padx=(0, 10))

            template[troop] = {
                "priority_number": priority,
                "min_value": min,
                "max_value": max,
                "population": troop_population,
            }

            last_row_number += 1

        template = {}
        fake_templates = settings["scheduler"]["fake_templates"]
        last_row_number = 4

        template_window = TopLevel(
            title_text="Tribal Wars Bot",
            borderwidth=1,
            relief="groove",
        )

        frame = template_window.content_frame

        template_name = tk.StringVar()
        priority_number = tk.IntVar(value=1)
        troop_type = tk.StringVar()
        min_value = tk.IntVar()
        max_value = tk.IntVar()

        top_frame = ttk.Frame(frame)
        top_frame.grid(row=0, column=0, columnspan=5, padx=5, pady=(5, 10))
        top_frame.columnconfigure(0, weight=1)

        ttk.Label(
            top_frame,
            text="Szablon dobierania jednostek",
        ).grid(row=0, column=0, padx=5)

        info = ttk.Label(top_frame, image=self.main_window.images.info)
        info.grid(row=0, column=1)

        ToolTip(
            info,
            text="Kolejność dobierania jednostek zaczyna się od tych o najwyższym priorytecie.\n\n"
            "Najwyższy = 1, najniższy = 9\n\n"
            "Min oznacza minimalną ilość wybranej jednostki która musi się znaleźć w wysyłanym fejku. \n\n"
            "Jednostki są dobierane po kolei na podstawie priorytetu aż do momentu spełnienia warunku "
            "minimalnej liczby populacji.\n\n"
            "Przykład:\n\n"
            "Priorytet Jednostka Min Max\n"
            "1 Katapulta 1 5\n"
            "2 Zwiadowca 0 25\n"
            "3 Topornik 0 25\n"
            "4 Lekka kawaleria 0 10\n\n"
            "W fejku musi się znaleźć min 1 katapulta do max 5. "
            "Dzięki temu mamy pewność, że fejk będzie miał prędkość tarana. "
            "Jeśli minimalny limit populacji nie został osiągnięty w pierwszym kroku, zostanie dobrana "
            "odpowiednia ilość jednostek niższego priorytetu w tym przypadku zwiadowców. "
            "Krok ten będzie powatarzany aż do momentu spełnienia limitu minimalnej liczby populacji lub "
            "wyczerpania się wszystkich możliwości.",
            wraplength=500,
            topmost=True,
        )

        ttk.Label(frame, text="Nazwa szablonu:").grid(
            row=1, column=0, columnspan=5, padx=10, pady=10, sticky=tk.W
        )

        ttk.Entry(frame, textvariable=template_name).grid(
            row=1, column=0, columnspan=5, padx=10, pady=10, sticky=tk.E
        )

        ttk.Label(frame, text="Priorytet").grid(row=2, column=0, padx=(10, 5))
        ttk.Label(frame, text="Jednostka").grid(row=2, column=1, padx=5)
        ttk.Label(frame, text="Min").grid(row=2, column=2, padx=5)
        ttk.Label(frame, text="Max").grid(row=2, column=3, padx=(5, 10))

        choose_priority_number = ttk.Combobox(
            frame, textvariable=priority_number, width=3, justify=tk.CENTER
        )
        choose_priority_number.grid(row=3, column=0, padx=(10, 5), pady=(0, 5))
        choose_priority_number["state"] = "readonly"
        choose_priority_number["values"] = tuple(num for num in range(1, 10))

        choose_troop_type = ttk.Combobox(
            frame, textvariable=troop_type, width=14, justify=tk.CENTER
        )
        choose_troop_type.grid(row=3, column=1, padx=5, pady=(0, 5))
        choose_troop_type["state"] = "readonly"
        choose_troop_type["values"] = (
            "Pikinier",
            "Miecznik",
            "Topornik",
            "Łucznik",
            "Zwiadowca",
            "Lekka kawaleria",
            "Łucznik konny",
            "Ciężka kawaleria",
            "Taran",
            "Katapulta",
        )

        ttk.Entry(frame, textvariable=min_value, width=4, justify=tk.CENTER).grid(
            row=3, column=2, padx=5, pady=(0, 5)
        )
        ttk.Entry(frame, textvariable=max_value, width=4, justify=tk.CENTER).grid(
            row=3, column=3, padx=(5, 10), pady=(0, 5)
        )
        ttk.Button(
            frame,
            bootstyle="primary.Link.TButton",
            image=self.main_window.images.plus,
            command=add_to_template,
        ).grid(row=3, column=4, padx=(0, 10), pady=(0, 5))

        def create_template_button_command() -> None:
            if not any(template[troop]["min_value"] for troop in template):
                custom_error(
                    "Przynajmniej jedna jednostka musi mieć wartość minimalną większą od 0",
                    parent=frame,
                )
                return
            fake_templates[template_name.get()] = template
            template_window.destroy(),
            self.redraw_availabe_templates(settings=settings)

        ttk.Button(
            frame, text="Utwórz szablon", command=create_template_button_command
        ).grid(row=50, column=0, columnspan=5, pady=(10, 10))

        center(template_window, self.parent)
        template_window.attributes("-alpha", 1.0)

    def redraw_availabe_templates(self, settings: dict) -> None:
        forget_row(self.frame, rows_beetwen=(19, 40))
        self.available_templates(settings=settings)
        self.frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def show_existing_schedule(self, settings: dict, main_window) -> None:
        if hasattr(self, "existing_schedule_window"):
            if self.existing_schedule_window.winfo_exists():
                return

        self.existing_schedule_window = TopLevel(title_text="Tribal Wars Bot")

        content_frame = self.existing_schedule_window.content_frame

        self.coldata = [
            {"text": "Data wysyłki", "stretch": False, "anchor": "center"},
            {"text": "Świat", "stretch": False, "anchor": "center"},
            {"text": "Komenda", "stretch": False, "anchor": "center"},
            {"text": "Rodzaj", "stretch": False, "anchor": "center"},
            {"text": "Wioska startowa", "stretch": False, "anchor": "center"},
            {"text": "Wioska docelowa", "stretch": False, "anchor": "center"},
            {"text": "Data wejścia wojsk", "stretch": False, "anchor": "center"},
        ]

        translate = {
            "target_support": "wsparcie",
            "target_attack": "atak",
            "send_all": "wyślij wszystkie",
            "send_fake": "wyślij fejk",
            "send_my_template": "własny szablon",
        }

        server_world = settings["server_world"]
        schedule: list = settings["scheduler"]["ready_schedule"]
        rowdata = [
            tuple(
                (
                    datetime.strftime(
                        datetime.fromtimestamp(row["send_time"]), "%d.%m.%Y %H:%M:%S:%f"
                    )[:-3],
                    server_world,
                    translate[row["command"]],
                    translate[row["template_type"]],
                    row["send_from"],
                    row["send_to"],
                    row["arrival_time"],
                )
            )
            for row in schedule
        ]

        table = Tableview(
            master=content_frame,
            coldata=self.coldata,
            rowdata=rowdata,
            datasource=schedule,
            paginated=True,
            searchable=True,
            stripecolor=("gray14", None),
            autofit=True,
            autoalign=False,
        )
        table.grid(row=0, column=0)

        center(window=self.existing_schedule_window, parent=main_window.master)
        self.existing_schedule_window.attributes("-alpha", 1.0)


class Gathering(ScrollableFrame):
    """Content and functions to put in notebook frame f2 named 'Zbieractwo'."""

    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ) -> None:

        super().__init__(parent)

        self.entries_content = entries_content
        self.entries_content["gathering"] = {}
        self.entries_content["gathering_troops"] = {
            "spear": {
                "left_in_village": tk.IntVar(),
                "send_max": tk.IntVar(),
            },
            "sword": {
                "left_in_village": tk.IntVar(),
                "send_max": tk.IntVar(),
            },
            "axe": {
                "left_in_village": tk.IntVar(),
                "send_max": tk.IntVar(),
            },
            "archer": {
                "left_in_village": tk.IntVar(),
                "send_max": tk.IntVar(),
            },
            "light": {
                "left_in_village": tk.IntVar(),
                "send_max": tk.IntVar(),
            },
            "marcher": {
                "left_in_village": tk.IntVar(),
                "send_max": tk.IntVar(),
            },
            "heavy": {
                "left_in_village": tk.IntVar(),
                "send_max": tk.IntVar(),
            },
            "knight": {
                "left_in_village": tk.IntVar(),
                "send_max": tk.IntVar(),
            },
        }

        gathering_troops = self.entries_content["gathering_troops"]

        self.entries_content["gathering"]["active"] = tk.BooleanVar()
        self.active_gathering = ttk.Checkbutton(
            self.frame,
            text="Aktywuj zbieractwo",
            variable=self.entries_content["gathering"]["active"],
            onvalue=True,
            offvalue=False,
        )
        self.active_gathering.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
        self.active_gathering.configure(
            command=partial(
                change_state,
                self.frame,
                "active",
                self.entries_content["gathering"],
                True,
                self.active_gathering,
            ),
        )

        ttk.Separator(self.frame, orient="horizontal").grid(
            row=1, column=0, columnspan=2, sticky=("W", "E")
        )

        # ----------------------------------------------------------------
        ttk.Label(self.frame, text="Ustawienia").grid(
            row=5, columnspan=2, padx=5, pady=(20, 15), sticky="W"
        )

        ttk.Label(self.frame, text="Grupa zbieractwa").grid(
            row=6, column=0, padx=(25, 5), pady=5, sticky="W"
        )

        self.entries_content["gathering_group"] = tk.StringVar()
        self.gathering_group = ttk.Combobox(
            self.frame,
            textvariable=self.entries_content["gathering_group"],
            justify="center",
            width=16,
            state="readonly",
        )
        self.gathering_group.grid(row=6, column=1, padx=(5, 25), pady=5, sticky="E")
        self.gathering_group.set("Wybierz grupę")
        self.gathering_group["values"] = settings["groups"]

        self.gathering_max_resources = ttk.Label(
            self.frame, text="Maks surowców do zebrania"
        )
        self.gathering_max_resources.grid(
            row=7, column=0, padx=(25, 5), pady=(10, 5), sticky="W"
        )

        self.entries_content["gathering_max_resources"] = tk.IntVar()
        self.gathering_max_resources_input = ttk.Entry(
            self.frame,
            textvariable=self.entries_content["gathering_max_resources"],
            justify="center",
            width=18,
        )
        self.gathering_max_resources_input.grid(
            row=7, column=1, padx=(5, 25), pady=(10, 5), sticky="E"
        )

        # ------------------------------------------------------------------------------------------------------------------
        ttk.Label(self.frame, text="Dozwolone jednostki do wysłania").grid(
            row=8, columnspan=2, padx=5, pady=(20, 15), sticky="W"
        )

        troops_frame = ttk.Frame(self.frame)
        troops_frame.grid(row=9, columnspan=2, sticky="EW")
        troops_frame.columnconfigure(1, weight=1)
        troops_frame.columnconfigure(2, weight=1)
        troops_frame.columnconfigure(4, weight=1)
        troops_frame.columnconfigure(5, weight=1)

        ttk.Label(troops_frame, text="Zostaw min").grid(row=8, column=1)
        ttk.Label(troops_frame, text="Wyślij max").grid(row=8, column=2)
        ttk.Label(troops_frame, text="Zostaw min").grid(row=8, column=4)
        ttk.Label(troops_frame, text="Wyślij max").grid(row=8, column=5, padx=(0, 25))

        def troop_entry_state(troop: str):
            if self.entries_content["gathering_troops"][troop]["use"].get():
                self.__getattribute__(f"{troop}_left").config(state="normal")
                self.__getattribute__(f"{troop}_max").config(state="normal")
            else:
                self.__getattribute__(f"{troop}_left").config(state="disabled")
                self.__getattribute__(f"{troop}_max").config(state="disabled")

        self.entries_content["gathering_troops"]["spear"]["use"] = tk.BooleanVar()
        self.gathering_spear = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.spear,
            compound="left",
            variable=self.entries_content["gathering_troops"]["spear"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("spear"),
        )
        self.gathering_spear.grid(row=9, column=0, padx=(25, 0), pady=5, sticky="W")
        self.spear_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["spear"]["left_in_village"],
            justify=tk.CENTER,
        )
        self.spear_left.grid(row=9, column=1, pady=5)
        self.spear_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["spear"]["send_max"],
            justify=tk.CENTER,
        )
        self.spear_max.grid(row=9, column=2, pady=5)

        self.entries_content["gathering_troops"]["light"]["use"] = tk.BooleanVar()
        self.gathering_light = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.light,
            compound="left",
            variable=self.entries_content["gathering_troops"]["light"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("light"),
        )
        self.gathering_light.grid(row=9, column=3, pady=5, sticky="W")
        self.light_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["light"]["left_in_village"],
            justify=tk.CENTER,
        )
        self.light_left.grid(row=9, column=4, pady=5)
        self.light_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["light"]["send_max"],
            justify=tk.CENTER,
        )
        self.light_max.grid(row=9, column=5, pady=5, padx=(0, 25))

        self.entries_content["gathering_troops"]["sword"]["use"] = tk.BooleanVar()
        self.gathering_sword = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.sword,
            compound="left",
            variable=self.entries_content["gathering_troops"]["sword"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("sword"),
        )
        self.gathering_sword.grid(row=10, column=0, padx=(25, 0), pady=5, sticky="W")
        self.sword_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["sword"]["left_in_village"],
            justify=tk.CENTER,
        )
        self.sword_left.grid(row=10, column=1, pady=5)
        self.sword_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["sword"]["send_max"],
            justify=tk.CENTER,
        )
        self.sword_max.grid(row=10, column=2, pady=5)

        self.entries_content["gathering_troops"]["marcher"]["use"] = tk.BooleanVar()
        self.gathering_marcher = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.marcher,
            compound="left",
            variable=self.entries_content["gathering_troops"]["marcher"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("marcher"),
        )
        self.gathering_marcher.grid(row=10, column=3, pady=5, sticky="W")
        self.marcher_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["marcher"]["left_in_village"],
            justify=tk.CENTER,
        )
        self.marcher_left.grid(row=10, column=4, pady=5)
        self.marcher_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["marcher"]["send_max"],
            justify=tk.CENTER,
        )
        self.marcher_max.grid(row=10, column=5, pady=5, padx=(0, 25))

        self.entries_content["gathering_troops"]["axe"]["use"] = tk.BooleanVar()
        self.gathering_axe = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.axe,
            compound="left",
            variable=self.entries_content["gathering_troops"]["axe"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("axe"),
        )
        self.gathering_axe.grid(row=11, column=0, padx=(25, 0), pady=5, sticky="W")
        self.axe_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["axe"]["left_in_village"],
            justify=tk.CENTER,
        )
        self.axe_left.grid(row=11, column=1, pady=5)
        self.axe_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["axe"]["send_max"],
            justify=tk.CENTER,
        )
        self.axe_max.grid(row=11, column=2, pady=5)

        self.entries_content["gathering_troops"]["heavy"]["use"] = tk.BooleanVar()
        self.gathering_heavy = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.heavy,
            compound="left",
            variable=self.entries_content["gathering_troops"]["heavy"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("heavy"),
        )
        self.gathering_heavy.grid(row=11, column=3, pady=5, sticky="W")
        self.heavy_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["heavy"]["left_in_village"],
            justify=tk.CENTER,
        )
        self.heavy_left.grid(row=11, column=4, pady=5)
        self.heavy_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["heavy"]["send_max"],
            justify=tk.CENTER,
        )
        self.heavy_max.grid(row=11, column=5, pady=5, padx=(0, 25))

        self.entries_content["gathering_troops"]["archer"]["use"] = tk.BooleanVar()
        self.gathering_archer = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.archer,
            compound="left",
            variable=self.entries_content["gathering_troops"]["archer"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("archer"),
        )
        self.gathering_archer.grid(
            row=12, column=0, padx=(25, 0), pady=(5, 10), sticky="W"
        )
        self.archer_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["archer"]["left_in_village"],
            justify=tk.CENTER,
        )
        self.archer_left.grid(row=12, column=1, pady=5)
        self.archer_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["archer"]["send_max"],
            justify=tk.CENTER,
        )
        self.archer_max.grid(row=12, column=2, pady=5)

        self.entries_content["gathering_troops"]["knight"]["use"] = tk.BooleanVar()
        self.gathering_knight = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.knight,
            compound="left",
            variable=self.entries_content["gathering_troops"]["knight"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("knight"),
        )
        self.gathering_knight.grid(row=12, column=3, pady=(5, 10), sticky="W")
        self.knight_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["knight"]["left_in_village"],
            justify=tk.CENTER,
        )
        self.knight_left.grid(row=12, column=4, pady=5)
        self.knight_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["knight"]["send_max"],
            justify=tk.CENTER,
        )
        self.knight_max.grid(row=12, column=5, pady=5, padx=(0, 25))

        # ------------------------------------------------------------------------------------------------------------------
        ttk.Label(self.frame, text="Poziomy zbieractwa do pominięcia").grid(
            row=13, columnspan=2, padx=5, pady=(20, 15), sticky="W"
        )

        f2_1 = ttk.Frame(self.frame)
        f2_1.grid(row=14, column=0, columnspan=2)

        self.entries_content["gathering"]["ommit"] = {}
        self.entries_content["gathering"]["ommit"][
            "first_level_gathering"
        ] = tk.BooleanVar()
        self.ommit_first_level_gathering = ttk.Checkbutton(
            f2_1,
            text="Pierwszy",
            variable=self.entries_content["gathering"]["ommit"][
                "first_level_gathering"
            ],
            onvalue=True,
            offvalue=False,
        )
        self.ommit_first_level_gathering.grid(
            row=14, column=0, padx=(25, 5), pady=(5, 10)
        )

        self.entries_content["gathering"]["ommit"][
            "second_level_gathering"
        ] = tk.BooleanVar()
        self.ommit_second_level_gathering = ttk.Checkbutton(
            f2_1,
            text="Drugi",
            variable=self.entries_content["gathering"]["ommit"][
                "second_level_gathering"
            ],
            onvalue=True,
            offvalue=False,
        )
        self.ommit_second_level_gathering.grid(row=14, column=1, padx=10, pady=(5, 10))

        self.entries_content["gathering"]["ommit"][
            "thrid_level_gathering"
        ] = tk.BooleanVar()
        self.ommit_thrid_level_gathering = ttk.Checkbutton(
            f2_1,
            text="Trzeci",
            variable=self.entries_content["gathering"]["ommit"][
                "thrid_level_gathering"
            ],
            onvalue=True,
            offvalue=False,
        )
        self.ommit_thrid_level_gathering.grid(row=14, column=2, padx=10, pady=(5, 10))

        self.entries_content["gathering"]["ommit"][
            "fourth_level_gathering"
        ] = tk.BooleanVar()
        self.ommit_fourth_level_gathering = ttk.Checkbutton(
            f2_1,
            text="Czwarty",
            variable=self.entries_content["gathering"]["ommit"][
                "fourth_level_gathering"
            ],
            onvalue=True,
            offvalue=False,
        )
        self.ommit_fourth_level_gathering.grid(
            row=14, column=3, padx=(5, 25), pady=(5, 10)
        )

        self.entries_content["gathering"]["stop_if_incoming_attacks"] = tk.BooleanVar()
        self.stop_if_incoming_attacks = ttk.Checkbutton(
            self.frame,
            text="Wstrzymaj wysyłkę wojsk gdy wykryto nadchodzące ataki",
            variable=self.entries_content["gathering"]["stop_if_incoming_attacks"],
            onvalue=True,
            offvalue=False,
        )
        self.stop_if_incoming_attacks.grid(
            row=15, column=0, columnspan=2, padx=25, pady=(10, 5)
        )


class Market(ScrollableFrame):
    """Content and functions to put in notebook frame f4 named 'Rynek'."""

    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ) -> None:

        super().__init__(parent)

        entries_content["market"] = {"wood": {}, "stone": {}, "iron": {}}
        market = entries_content["market"]

        market["premium_exchange"] = tk.BooleanVar()
        self.active_premium_exchange = ttk.Checkbutton(
            self.frame,
            text="Aktywuj giełdę premium",
            variable=market["premium_exchange"],
            onvalue=True,
            offvalue=False,
        )
        self.active_premium_exchange.configure(
            command=partial(
                change_state,
                self.frame,
                "premium_exchange",
                market,
                True,
                self.active_premium_exchange,
            ),
        )
        self.active_premium_exchange.grid(
            row=0, column=0, columnspan=2, padx=5, pady=20
        )

        ttk.Separator(self.frame, orient="horizontal").grid(
            row=1, column=0, columnspan=2, sticky=("W", "E")
        )

        # Maksymalny kurs sprzedaży
        ttk.Label(self.frame, text="Maksymalny kurs sprzedaży").grid(
            row=3, column=0, padx=5, pady=(20, 10), sticky="W"
        )

        self.wood_photo = tk.PhotoImage(file="icons//wood.png")
        ttk.Label(
            self.frame,
            text="Drewno",
            image=self.wood_photo,
            compound="left",
        ).grid(row=4, column=0, padx=(25, 5), pady=(10, 5), sticky="W")
        market["wood"]["max_exchange_rate"] = tk.IntVar()
        self.max_wood_exchange_rate = ttk.Entry(
            self.frame,
            textvariable=market["wood"]["max_exchange_rate"],
            justify="center",
            width=6,
        )
        self.max_wood_exchange_rate.grid(
            row=4, column=1, padx=(5, 25), pady=(10, 5), sticky="E"
        )

        self.stone_photo = tk.PhotoImage(file="icons//stone.png")
        ttk.Label(
            self.frame,
            text="Cegła",
            image=self.stone_photo,
            compound="left",
        ).grid(row=5, column=0, padx=(25, 5), pady=(10, 5), sticky="W")
        market["stone"]["max_exchange_rate"] = tk.IntVar()
        self.max_stone_exchange_rate = ttk.Entry(
            self.frame,
            textvariable=market["stone"]["max_exchange_rate"],
            justify="center",
            width=6,
        )
        self.max_stone_exchange_rate.grid(
            row=5, column=1, padx=(5, 25), pady=(10, 5), sticky="E"
        )

        self.iron_photo = tk.PhotoImage(file="icons//iron.png")
        ttk.Label(
            self.frame,
            text="Żelazo",
            image=self.iron_photo,
            compound="left",
        ).grid(row=6, column=0, padx=(25, 5), pady=(10, 5), sticky="W")
        market["iron"]["max_exchange_rate"] = tk.IntVar()
        self.max_iron_exchange_rate = ttk.Entry(
            self.frame,
            textvariable=market["iron"]["max_exchange_rate"],
            justify="center",
            width=6,
        )
        self.max_iron_exchange_rate.grid(
            row=6, column=1, padx=(5, 25), pady=(10, 5), sticky="E"
        )

        # Zapas surowców w wioskach
        ttk.Label(self.frame, text="Zapas surowców w wioskach").grid(
            row=9, column=0, padx=5, pady=(15, 10), sticky="W"
        )

        ttk.Label(
            self.frame,
            text="Drewno",
            image=self.wood_photo,
            compound="left",
        ).grid(row=10, column=0, padx=(25, 5), pady=(10, 5), sticky="W")
        market["wood"]["leave_in_storage"] = tk.IntVar()
        self.min_wood_left_in_storage = ttk.Entry(
            self.frame,
            textvariable=market["wood"]["leave_in_storage"],
            justify="center",
            width=6,
        )
        self.min_wood_left_in_storage.grid(
            row=10, column=1, padx=(5, 25), pady=(10, 5), sticky="E"
        )
        ttk.Label(
            self.frame,
            text="Cegła",
            image=self.stone_photo,
            compound="left",
        ).grid(row=11, column=0, padx=(25, 5), pady=(10, 5), sticky="W")
        market["stone"]["leave_in_storage"] = tk.IntVar()
        self.min_stone_left_in_storage = ttk.Entry(
            self.frame,
            textvariable=market["stone"]["leave_in_storage"],
            justify="center",
            width=6,
        )
        self.min_stone_left_in_storage.grid(
            row=11, column=1, padx=(5, 25), pady=(10, 5), sticky="E"
        )
        ttk.Label(
            self.frame,
            text="Żelazo",
            image=self.iron_photo,
            compound="left",
        ).grid(row=12, column=0, padx=(25, 5), pady=(10, 5), sticky="W")
        market["iron"]["leave_in_storage"] = tk.IntVar()
        self.min_iron_left_in_storage = ttk.Entry(
            self.frame,
            textvariable=market["iron"]["leave_in_storage"],
            justify="center",
            width=6,
        )
        self.min_iron_left_in_storage.grid(
            row=12, column=1, padx=(5, 25), pady=(10, 5), sticky="E"
        )

        # Pozostałe ustawienia
        ttk.Label(self.frame, text="Pozostałe ustawienia").grid(
            row=13, column=0, padx=5, pady=(15, 10), sticky="W"
        )

        ttk.Label(self.frame, text="Sprawdzaj kursy surowców co [min]").grid(
            row=14, column=0, padx=(25, 5), pady=(10, 5), sticky="W"
        )
        market["check_every"] = tk.IntVar()
        ttk.Entry(
            self.frame,
            textvariable=market["check_every"],
            justify="center",
            width=6,
        ).grid(row=14, column=1, padx=(5, 25), pady=(10, 5), sticky="E")

        def show_label_and_text_widget() -> None:
            def clear_text_widget(event) -> None:
                if self.villages_to_ommit_text.get("1.0", "1.5") == "Wklej":
                    self.villages_to_ommit_text.delete("1.0", "end")
                    self.villages_to_ommit_text.unbind("<Button-1>")

            def add_villages_list() -> None:
                if self.villages_to_ommit_text.compare("end-1c", "==", "1.0"):
                    self.villages_to_ommit_text.insert(
                        "1.0",
                        "Wklej wioski w formacie XXX|YYY które chcesz aby były pomijane. "
                        "Wioski powinny być oddzielone spacją, tabulatorem lub enterem. "
                        "Możesz także podać cały kontynet np. k45 lub K45",
                    )
                    return
                if self.villages_to_ommit_text.get("1.0", "1.5") == "Wklej":
                    market["market_exclude_villages"].set("")
                else:
                    market["market_exclude_villages"].set(
                        self.villages_to_ommit_text.get("1.0", "end")
                    )
                    settings["market"][
                        "market_exclude_villages"
                    ] = self.villages_to_ommit_text.get("1.0", "end")
                self.villages_to_ommit_text.grid_forget()
                self.confirm_button.grid_forget()

                self.success_label = ttk.Label(self.frame, text="Dodano!")
                self.success_label.grid(
                    row=21, column=0, columnspan=2, padx=5, pady=(10, 15)
                )
                self.frame.update()
                self.frame.after(
                    1500,
                    lambda: [
                        self.success_label.grid_forget(),
                        self.frame.update_idletasks(),
                        self.canvas.itemconfig(
                            self.canvas_frame,
                            height=self.frame.winfo_reqheight(),
                        ),
                    ],
                )
                del self.villages_to_ommit_text

            if hasattr(self, "villages_to_ommit_text"):
                self.villages_to_ommit_text.grid_forget()
                self.confirm_button.grid_forget()
                del self.villages_to_ommit_text
                return

            self.villages_to_ommit_text = tk.Text(
                self.frame, height=6, width=50, wrap="word"
            )
            self.villages_to_ommit_text.grid(
                row=21, column=0, columnspan=2, padx=5, pady=10
            )
            if (
                settings["market"]["market_exclude_villages"]
                and settings["market"]["market_exclude_villages"] != "0"
            ):
                self.villages_to_ommit_text.insert(
                    "1.0", settings["market"]["market_exclude_villages"]
                )
            else:
                self.villages_to_ommit_text.insert(
                    "1.0",
                    "Wklej wioski w formacie XXX|YYY które chcesz aby były pomijane. "
                    "Wioski powinny być oddzielone spacją, tabulatorem lub enterem. "
                    "Możesz także podać cały kontynet np. k45 lub K45",
                )

            self.confirm_button = ttk.Button(
                self.frame, text="Dodaj", command=add_villages_list
            )
            self.confirm_button.grid(
                row=22, column=0, columnspan=2, padx=5, pady=(5, 10)
            )
            self.frame.update_idletasks()
            self.canvas.itemconfig(
                self.canvas_frame,
                height=self.frame.winfo_reqheight(),
            )
            self.canvas.after_idle(lambda: self.canvas.yview_moveto(1))
            self.villages_to_ommit_text.bind("<Button-1>", clear_text_widget)
            self.villages_to_ommit_text.bind("<Enter>", self._unbound_to_mousewheel)
            self.villages_to_ommit_text.bind("<Leave>", self._bound_to_mousewheel)

        market["market_exclude_villages"] = tk.StringVar()
        self.add_village_exceptions_button = ttk.Button(
            self.frame,
            text="Dodaj wioski do pominięcia",
            command=show_label_and_text_widget,
        )
        self.add_village_exceptions_button.grid(
            row=20, column=0, columnspan=2, padx=5, pady=(25, 5)
        )


class Settings(ScrollableFrame):
    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ) -> None:

        super().__init__(parent)

        self.frame.rowconfigure(5, weight=1)

        self.entries_content = entries_content

        ttk.Label(self.frame, text="Wybierz serwer i numer świata").grid(
            row=0, column=0, padx=5, pady=(15, 5), sticky="W"
        )

        entries_content["game_url"] = tk.StringVar()
        self.game_url = ttk.Combobox(
            self.frame,
            textvariable=entries_content["game_url"],
            state="readonly",
            justify="center",
            width=20,
        )
        self.game_url.grid(row=0, column=1, padx=5, pady=(15, 5))
        self.game_url.set("Wybierz serwer")
        self.game_url["values"] = [
            "die-staemme.de",
            "staemme.ch",
            "tribalwars.net",
            "tribalwars.nl",
            "plemiona.pl",
            "tribalwars.se",
            "tribalwars.com.br",
            "tribalwars.com.pt",
            "divokekmeny.cz",
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

        entries_content["world_number"] = tk.StringVar()
        self.world_number_input = ttk.Entry(
            self.frame,
            textvariable=entries_content["world_number"],
            width=5,
            justify="center",
        )
        self.world_number_input.grid(row=0, column=2, padx=5, pady=(15, 5), sticky="E")

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

        ttk.Label(self.frame, text="Dostępne grupy wiosek").grid(
            row=2, column=0, padx=(5, 0), pady=(10), sticky="W"
        )
        self.villages_groups = ttk.Combobox(
            self.frame,
            state="readonly",
            justify="center",
        )
        self.villages_groups.grid(row=2, column=1, padx=(0), pady=(10))
        self.villages_groups.set("Dostępne grupy")
        self.villages_groups["values"] = settings["groups"]

        # Update available groups

        ttk.Button(
            self.frame,
            image=main_window.images.refresh,
            bootstyle="primary.Link.TButton",
            command=lambda: threading.Thread(
                target=lambda: main_window.check_groups(settings=settings),
                name="checking_groups",
                daemon=True,
            ).start(),
        ).grid(row=2, column=2, padx=5, pady=(10), sticky="E")

        # Coin mine

        self.mine_coin_frame = ttk.Frame(self.frame)
        self.mine_coin_frame.grid(row=4, column=0, columnspan=3, sticky=ttk.NSEW)
        self.mine_coin_frame.columnconfigure(0, weight=1)
        self.mine_coin_frame.columnconfigure(1, weight=1)

        entries_content["mine_coin"] = tk.BooleanVar()
        self.check_mine_coin = ttk.Checkbutton(
            self.mine_coin_frame,
            text="Wybijanie monet",
            variable=entries_content["mine_coin"],
            onvalue=True,
            offvalue=False,
        )
        self.check_mine_coin.grid(row=0, column=0, columnspan=2, padx=5, pady=10)

        self.villages_to_mine_coin = ttk.Entry(
            self.mine_coin_frame,
            justify=ttk.CENTER,
            width=7,
        )
        self.villages_to_mine_coin.grid(row=1, column=0, padx=5, pady=5, sticky=ttk.E)

        def add_village_to_mine_coin_villages_list() -> None:
            village = self.villages_to_mine_coin.get()
            villages = app_functions.get_villages_id(settings=settings)
            if village in villages:
                village_id = villages[village][:-1]
            else:
                villages = app_functions.get_villages_id(settings=settings, update=True)
                if village not in villages:
                    custom_error(
                        message=f"Wioska {village} nie istnieje.", parent=parent
                    )
                    return
                village_id = villages[village][:-1]
            settings.setdefault("villages_to_mine_coin", [])
            settings["villages_to_mine_coin"].append(
                {"coords": village, "id": village_id}
            )

        self.add_village_to_mine_coin = ttk.Button(
            self.mine_coin_frame,
            text="Dodaj",
            command=add_village_to_mine_coin_villages_list,
        )
        self.add_village_to_mine_coin.grid(
            row=1, column=1, padx=5, pady=5, sticky=ttk.W
        )

        # Disable stable release
        entries_content["stable_release"] = ttk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.frame,
            text="Zezwól na beta wersje aplikacji",
            onvalue=False,
            offvalue=True,
            variable=entries_content["stable_release"],
        ).grid(row=5, columnspan=3, pady=10, sticky=ttk.S)

        # Account information

        self.acc_info_frame = ttk.Labelframe(
            self.frame, text="Informacje o koncie", labelanchor="n"
        )
        self.acc_info_frame.grid(
            row=10, column=0, columnspan=3, padx=5, pady=5, sticky=("W", "S", "E")
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
            text="Przedłuż ważność konta",
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
                main_window.notebook.select(4)
                custom_error(message=message, parent=self.parent)
                if "world_number" in settings:
                    self.entries_content["world_number"].set(settings["world_number"])

            if not self.entries_content["world_number"].get().isnumeric():
                on_error("Numer świata powinien składać się z samych cyfr.")
                return

            if not main_window.add_new_world(
                settings=settings,
                game_url=self.entries_content["game_url"].get(),
                world_number=self.entries_content["world_number"].get(),
                entry_change=True,
            ):
                on_error("Błąd. Upewnij się, że taki świat nadal istnieje.")

        if (
            settings["world_number"] != self.entries_content["world_number"].get()
            or settings["game_url"] != self.entries_content["game_url"].get()
        ):

            on_focus_out()


class Notifications(ScrollableFrame):
    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ) -> None:

        super().__init__(parent)

        entries_content["notifications"] = {}
        notifications = entries_content["notifications"]

        ttk.Label(self.frame, text="Etykiety ataków").grid(
            row=0, column=0, padx=5, pady=20, sticky="W"
        )

        notifications["check_incoming_attacks"] = tk.BooleanVar()

        def change_entry(value, widget) -> None:
            if value.get():
                widget.config(state="normal")
            else:
                widget.config(state="disabled")

        self.check_incoming_attacks = ttk.Checkbutton(
            self.frame,
            text="Etykiety nadchodzących ataków",
            variable=notifications["check_incoming_attacks"],
            onvalue=True,
            offvalue=False,
            command=lambda: change_entry(
                value=notifications["check_incoming_attacks"],
                widget=self.check_incoming_attacks_sleep_time,
            ),
        )
        self.check_incoming_attacks.grid(
            row=7, column=0, columnspan=2, padx=(25, 5), pady=(0, 10), sticky="W"
        )

        self.check_incoming_attacks_label = ttk.Label(
            self.frame, text="Twórz etykiety ataków co [min]"
        )
        self.check_incoming_attacks_label.grid(
            row=8, column=0, padx=(25, 5), pady=5, sticky="W"
        )

        notifications["check_incoming_attacks_sleep_time"] = tk.IntVar()
        self.check_incoming_attacks_sleep_time = ttk.Entry(
            self.frame,
            textvariable=notifications["check_incoming_attacks_sleep_time"],
            width=5,
            justify="center",
        )
        self.check_incoming_attacks_sleep_time.grid(
            row=8, column=1, padx=(5, 25), pady=5, sticky="E"
        )

        ttk.Label(self.frame, text="Powiadomienia").grid(
            row=9, column=0, padx=5, pady=(20, 10), sticky="W"
        )

        notifications["email_notifications"] = tk.BooleanVar()
        self.email_notifications = ttk.Checkbutton(
            self.frame,
            text="Powiadomienia email o idących grubasach",
            variable=notifications["email_notifications"],
            onvalue=True,
            offvalue=False,
            command=lambda: change_entry(
                value=notifications["email_notifications"],
                widget=self.email_notifications_entry,
            ),
        )
        self.email_notifications.grid(
            row=10, column=0, columnspan=2, padx=(25, 5), pady=10, sticky="W"
        )

        ttk.Label(self.frame, text="Wyślij powiadomienia na adres:").grid(
            row=11, column=0, padx=(25, 5), pady=10, sticky="W"
        )
        notifications["email_address"] = tk.StringVar()
        self.email_notifications_entry = ttk.Entry(
            self.frame,
            textvariable=notifications["email_address"],
            justify="center",
        )
        self.email_notifications_entry.grid(
            row=11, column=1, padx=(5, 25), pady=10, sticky="E"
        )

        notifications["sms_notifications"] = tk.BooleanVar()
        self.sms_notifications = ttk.Checkbutton(
            self.frame,
            text="Powiadomienia sms o idących grubasach",
            variable=notifications["sms_notifications"],
            onvalue=True,
            offvalue=False,
            command=lambda: change_entry(
                value=notifications["sms_notifications"],
                widget=self.sms_notifications_entry,
            ),
        )
        self.sms_notifications.grid(
            row=12, column=0, columnspan=2, padx=(25, 5), pady=10, sticky="W"
        )

        ttk.Label(self.frame, text="Wyślij powiadomienia na numer:").grid(
            row=13, column=0, padx=(25, 5), pady=10, sticky="W"
        )
        notifications["phone_number"] = tk.StringVar()
        self.sms_notifications_entry = ttk.Entry(
            self.frame,
            textvariable=notifications["phone_number"],
            justify="center",
        )
        self.sms_notifications_entry.grid(
            row=13, column=1, padx=(5, 25), pady=10, sticky="E"
        )
        ToolTip(
            self.sms_notifications_entry,
            text=(
                "Dostępne są tylko polskie 9 cyfrowe numery.\n\n"
                "Przykładowy numer: 739162666"
            ),
            topmost=True,
        )

        notifications["sound_notifications"] = tk.BooleanVar()
        self.sound_notifications = ttk.Checkbutton(
            self.frame,
            text="Powiadomienia dźwiękowe o idących grubasach",
            variable=notifications["sound_notifications"],
            onvalue=True,
            offvalue=False,
        )
        self.sound_notifications.grid(
            row=14, column=0, columnspan=2, padx=(25, 5), pady=10, sticky="W"
        )


class NavigationBar(ScrollableFrame):
    def __init__(self, main_window: "MainWindow", parent: ttk.Frame = None) -> None:
        self.header = ttk.Frame(parent)
        self.header.grid(row=0, column=0, pady=5, sticky=tk.NS)
        super().__init__(self.header, max_width=False, show=True)
        self.footer = ttk.Frame(parent)
        self.footer.grid(row=1, column=0, sticky=tk.EW)
        self.footer.columnconfigure(0, weight=1)

        # Header
        # region
        self.home = ttk.Button(
            self.frame,
            text="Informacje",
            command=lambda: main_window.farm.show(),
        )
        self.home.grid(row=0, column=0, sticky=tk.EW)

        self.farm = ttk.Button(
            self.frame,
            text="Farma",
            command=lambda: main_window.farm.show(),
        )
        self.farm.grid(row=1, column=0, sticky=tk.EW)

        self.gathering = ttk.Button(
            self.frame,
            text="Zbieractwo",
            command=lambda: main_window.gathering.show(),
        )
        self.gathering.grid(row=2, column=0, sticky=tk.EW)

        self.market = ttk.Button(
            self.frame,
            text="Rynek",
            command=lambda: main_window.market.show(),
        )
        self.market.grid(row=3, column=0, sticky=tk.EW)

        self.coins = ttk.Button(
            self.frame,
            text="Monety",
            state="disabled",
            command=lambda: main_window.notifications.show(),
        )
        self.coins.grid(row=4, column=0, sticky=tk.EW)

        self.schedule = ttk.Button(
            self.frame,
            text="Planer",
            command=lambda: main_window.schedule.show(),
        )
        self.schedule.grid(row=5, column=0, sticky=tk.EW)

        self.dodge = ttk.Button(
            self.frame,
            text="Uniki",
            state="disabled",
            command=lambda: main_window.notifications.show(),
        )
        self.dodge.grid(row=6, column=0, sticky=tk.EW)

        self.counter_attack = ttk.Button(
            self.frame,
            text="Kontra",
            state="disabled",
            command=lambda: main_window.notifications.show(),
        )
        self.counter_attack.grid(row=7, column=0, sticky=tk.EW)

        self.manager = ttk.Button(
            self.frame,
            text="Menadżer Konta",
            state="disabled",
            command=lambda: main_window.notifications.show(),
        )
        self.manager.grid(row=8, column=0, sticky=tk.EW)

        self.notifications = ttk.Button(
            self.frame,
            text="Powiadomienia",
            command=lambda: main_window.notifications.show(),
        )
        self.notifications.grid(row=9, column=0, sticky=tk.EW)
        # endregion

        # Footer
        # region
        self.control_panel = ttk.Label(
            self.footer,
            image=main_window.images.settings,
            cursor="hand2",
        )
        self.control_panel.grid(row=0, column=0)

        def control_panel_enter(event) -> None:
            self.control_panel.config(image=main_window.images.settings_hover)

        def control_panel_leave(event) -> None:
            self.control_panel.config(image=main_window.images.settings)

        self.control_panel.bind("<Enter>", control_panel_enter)
        self.control_panel.bind("<Leave>", control_panel_leave)
        self.control_panel.bind(
            "<Button-1>", lambda _: main_window.control_panel.show()
        )

        self.run_button = ttk.Label(
            self.footer, image=main_window.images.start, cursor="hand2"
        )
        self.run_button.grid(row=1, column=0, pady=20)

        def run_button_enter(event) -> None:
            self.run_button.config(image=main_window.images.start_hover)

        def run_button_leave(event) -> None:
            self.run_button.config(image=main_window.images.start)

        def stop_button_enter(event) -> None:
            self.run_button.config(image=main_window.images.stop_hover)

        def stop_button_leave(event) -> None:
            self.run_button.config(image=main_window.images.stop)

        def start_or_stop_bot(event) -> None:
            if not main_window.running:
                main_window.running = True
                # threading.Thread(
                #     target=lambda: main_window.run(settings=settings),
                #     name="main_function",
                #     daemon=True,
                # ).start()
                self.run_button.unbind("<Enter>")
                self.run_button.unbind("<Leave>")
                self.run_button.bind("<Enter>", stop_button_enter)
                self.run_button.bind("<Leave>", stop_button_leave)
                self.run_button.config(image=main_window.images.stop)
            else:
                main_window.running = False
                self.run_button.unbind("<Enter>")
                self.run_button.unbind("<Leave>")
                self.run_button.bind("<Enter>", run_button_enter)
                self.run_button.bind("<Leave>", run_button_leave)
                self.run_button.config(image=main_window.images.start)

        self.run_button.bind("<Enter>", run_button_enter)
        self.run_button.bind("<Leave>", run_button_leave)
        self.run_button.bind("<Button-1>", start_or_stop_bot)
        # endregion

        def set_canvas_size(event=None):
            self.canvas.config(width=self.frame.winfo_reqwidth())

        self.frame.bind("<Map>", set_canvas_size)


class MainWindow:

    entries_content: dict[str, dict | tk.Variable] = {}
    settings_by_worlds: dict[str, dict] = {}

    def __init__(
        self, master: tk.Tk, driver: webdriver.Chrome, settings: dict[str]
    ) -> None:
        self.captcha_counter = ttk.IntVar()
        self.driver = driver
        self.master = master
        self.running = False

        master.geometry("620x700")
        master.attributes("-alpha", 0.0)
        master.iconbitmap(default="icons//ikona.ico")
        master.title("Tribal Wars 24/7")
        master.overrideredirect(True)
        master.attributes("-topmost", 1)

        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        # All used images -> one time load
        class Images(NamedTuple):
            start: tk.PhotoImage = tk.PhotoImage(file="icons//start.png")
            start_hover: tk.PhotoImage = tk.PhotoImage(file="icons//start_hover.png")
            settings: tk.PhotoImage = tk.PhotoImage(file="icons//settings.png")
            settings_hover: tk.PhotoImage = tk.PhotoImage(
                file="icons//settings_hover.png"
            )
            stop: tk.PhotoImage = tk.PhotoImage(file="icons//stop.png")
            stop_hover: tk.PhotoImage = tk.PhotoImage(file="icons//stop_hover.png")
            exit: tk.PhotoImage = tk.PhotoImage(file="icons//exit.png")
            minimize: tk.PhotoImage = tk.PhotoImage(file="icons//minimize.png")
            plus: tk.PhotoImage = tk.PhotoImage(file="icons//plus.png")
            refresh: tk.PhotoImage = tk.PhotoImage(file="icons//refresh.png")
            info: tk.PhotoImage = tk.PhotoImage(file="icons//info.png")
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
            main: str = "Ratusz"
            barracks: str = "Koszary"
            stable: str = "Stajnia"
            garage: str = "Warsztat"
            snob: str = "Pałac"
            smith: str = "Kuźnia"
            place: str = "Plac"
            statue: str = "Piedestał"
            market: str = "Rynek"
            wood: str = "Tartak"
            stone: str = "Cegielnia"
            iron: str = "Huta żelaza"
            farm: str = "Zagroda"
            storage: str = "Spichlerz"
            wall: str = "Mur"

        self.buildings = Buildings()

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

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=1, column=2, sticky=tk.NSEW)
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
            app_functions.save_settings_to_files(
                settings=settings, settings_by_worlds=self.settings_by_worlds
            )
            master.destroy()

        self.exit_button = ttk.Button(
            self.custom_bar,
            bootstyle="primary.Link.TButton",
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
        self.title_timer.bind(
            "<Button-1>", lambda event: self.show_jobs_to_do_window(event)
        )
        # endregion

        # navigation_bar

        self.navigation = NavigationBar(self, parent=self.navigation_frame)

        # content_frame

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

        self.control_panel = Settings(
            parent=self.content_frame,
            main_window=self,
            entries_content=self.entries_content,
            settings=settings,
        )

        self.notifications = Notifications(
            parent=self.content_frame,
            main_window=self,
            entries_content=self.entries_content,
            settings=settings,
        )

        # Other things
        fill_entry_from_settings(entries=self.entries_content, settings=settings)
        save_entry_to_settings(entries=self.entries_content, settings=settings)

        master.unbind_class("TCombobox", "<MouseWheel>")

        master.bind_class(
            "TEntry",
            "<ButtonRelease-1>",
            lambda event: on_button_release(event, master),
        )

        master.withdraw()

    @log_errors()
    def add_new_world(
        self,
        settings: dict,
        game_url: str,
        world_number: str,
        entry_change: bool = False,
    ) -> bool:
        def get_world_config() -> bool:
            response = requests.get(
                f"https://{server_world}.{game_url}/interface.php?func=get_config"
            )
            try:
                world_config = xmltodict.parse(response.content)
            except:
                return False

            settings["world_config"] = {
                "archer": world_config["config"]["game"]["archer"],
                "church": world_config["config"]["game"]["church"],
                "knight": world_config["config"]["game"]["knight"],
                "watchtower": world_config["config"]["game"]["watchtower"],
                "fake_limit": world_config["config"]["game"]["fake_limit"],
                "start_hour": world_config["config"]["night"]["start_hour"],
                "end_hour": world_config["config"]["night"]["end_hour"],
            }
            return True

        def set_additional_settings(
            game_url: str, country_code: str, server_world: str
        ) -> None:
            settings["game_url"] = game_url
            settings["country_code"] = country_code
            settings["server_world"] = server_world
            settings["groups"] = ["wszystkie"]
            settings["scheduler"]["ready_schedule"].clear()
            for template in ("A", "B", "C"):
                self.entries_content[template]["farm_rules"]["loot"].set("mix_loot")

        country_code = game_url[game_url.rfind(".") + 1 :]
        server_world = f"{country_code}{world_number}"

        if not os.path.isdir("settings"):
            os.mkdir("settings")

        # Takie ustawienia już istnieją
        if server_world in self.settings_by_worlds:
            if entry_change:
                self.notebook.select(4)
                custom_error("Ustawienia tego świata już istnieją!", parent=self.master)
                self.entries_content["game_url"].set(settings["game_url"])
                self.entries_content["world_number"].set(settings["world_number"])
                self.control_panel.world_number_input.focus_set()
            else:
                custom_error(
                    "Ustawienia tego świata już istnieją!",
                    parent=self.master.focus_displayof().winfo_toplevel(),
                )
            return False

        # Ustawienia pierwszego świata
        elif len(self.settings_by_worlds) == 0 and entry_change:
            if not get_world_config():
                return False
            self.entries_content["world_in_title"].set(
                f"{country_code.upper()}{world_number.upper()}"
            )
            set_additional_settings(
                game_url=game_url, country_code=country_code, server_world=server_world
            )
            save_entry_to_settings(entries=self.entries_content, settings=settings)
            self.settings_by_worlds[server_world] = {}
            self.settings_by_worlds[server_world].update(settings)
            return True

        # Zmiana świata w obrębie wybranej konfiguracji ustawień
        elif entry_change:
            if not get_world_config():
                return False
            del self.settings_by_worlds[settings["server_world"]]
            if os.path.exists(f'settings/{settings["server_world"]}.json'):
                os.remove(f'settings/{settings["server_world"]}.json')
            set_additional_settings(
                game_url=game_url, country_code=country_code, server_world=server_world
            )
            self.entries_content["world_in_title"].set(
                f"{country_code.upper()}{world_number.upper()}"
            )
            save_entry_to_settings(
                entries=self.entries_content,
                settings=settings,
            )
            self.settings_by_worlds[server_world] = {}
            self.settings_by_worlds[server_world].update(settings)
            return True

        # Dodanie nowych ustawień nieistniejącego jeszcze świata
        else:

            def set_default_entry_values(entries: dict | tk.Variable) -> None:
                """Ustawia domyślne wartości elementów GUI (entries_content)"""

                for key in entries:
                    if isinstance(entries[key], dict):
                        set_default_entry_values(entries=entries[key])
                    else:
                        entries[key].set(0)

            if settings["server_world"] in self.settings_by_worlds:
                save_entry_to_settings(
                    entries=self.entries_content,
                    settings=settings,
                    settings_by_worlds=self.settings_by_worlds,
                )
                self.settings_by_worlds[settings["server_world"]] = deepcopy(settings)
            else:
                save_entry_to_settings(entries=self.entries_content, settings=settings)

            if not get_world_config():
                return False

            # Set and configure gui entries for new world
            set_default_entry_values(entries=self.entries_content)
            self.entries_content["world_number"].set(value=world_number)
            self.entries_content["game_url"].set(value=game_url)
            self.entries_content["notifications"]["email_address"].set(
                value=self.user_data["email"]
            )
            self.entries_content["world_in_title"].set(
                f"{country_code.upper()}{world_number.upper()}"
            )
            # Set combobox deafult values
            for combobox in (
                self.farm.farm_group_A,
                self.farm.farm_group_B,
                self.farm.farm_group_C,
                self.gathering.gathering_group,
                self.control_panel.villages_groups,
            ):
                combobox["values"] = ["wszystkie"]
                combobox.set("wszystkie")
            # Set settings for new world
            set_additional_settings(
                game_url=game_url, country_code=country_code, server_world=server_world
            )

            invoke_checkbuttons(parent=self.master)
            self.schedule.template_type.set("")
            save_entry_to_settings(entries=self.entries_content, settings=settings)
            self.settings_by_worlds[server_world] = deepcopy(settings)
            settings.update(self.settings_by_worlds[server_world])

            return True

    def check_groups(self, settings: dict):

        if "server_world" not in settings:
            custom_error(
                message="Najpierw wybierz serwer i numer świata", parent=self.master
            )
            return
        self.control_panel.villages_groups.set("Updating..")
        save_entry_to_settings(entries=self.entries_content, settings=settings)
        app_functions.check_groups(
            self.driver,
            settings,
            *[
                self.farm.farm_group_A,
                self.farm.farm_group_B,
                self.farm.farm_group_C,
                self.gathering.gathering_group,
                self.control_panel.villages_groups,
            ],
        )
        self.control_panel.villages_groups.set("Dostępne grupy")

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

            # Odświeża okno planera
            self.schedule.redraw_availabe_templates(settings=settings)

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

            invoke_checkbuttons(parent=self.master)
            self.schedule.template_type.set("")

            self.entries_content["world_in_title"].set(f"{world_in_title}")
            self.world_chooser_window.destroy()

    def hide(self):
        self.master.attributes("-alpha", 0.0)
        self.master.overrideredirect(False)
        self.master.iconify()

        def show(event=None):
            self.master.overrideredirect(True)
            self.master.attributes("-alpha", 1.0)

        self.minimize_button.bind("<Map>", show)

    @log_errors(send_email=True)
    def run(self, settings: dict):
        """Uruchamia całego bota"""

        def on_func_stop() -> None:
            """Change few things on function quit/stop"""

            self.running = False
            self.run_button.config(text="Uruchom")

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
                        text="Zweryfikowany adres e-mail: Tak"
                    )
                    custom_error(
                        message="Adres e-mail został zweryfikowany",
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
        if not app_functions.paid(str(self.user_data["active_until"])):
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
            if not app_functions.paid(str(self.user_data["active_until"])):
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
            self.notebook.select(4)
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
            if _settings["farm_group"] == "Wybierz grupę":
                if any(_settings[letter]["active"] for letter in ("A", "B", "C")):
                    self.change_world(
                        server_world=server_world,
                        world_in_title=_settings["world_in_title"],
                        settings=settings,
                    )
                    self.notebook.select(0)
                    custom_error(
                        message="Nie wybrano grupy wiosek do farmienia.",
                        parent=self.master,
                    )
                    on_func_stop()
                    return
            # Gathering group
            if _settings["gathering_group"] == "Wybierz grupę":
                if _settings["gathering"]["active"]:
                    self.change_world(
                        server_world=server_world,
                        world_in_title=_settings["world_in_title"],
                        settings=settings,
                    )
                    self.notebook.select(1)
                    custom_error(
                        message="Nie wybrano grupy wiosek do zbieractwa.",
                        parent=self.master,
                    )
                    on_func_stop()
                    return

            # Check if user set sleep value bigger than 0 in choosed functions
            # Auto farm sleep time
            if _settings["farm_sleep_time"] == 0 and any(
                _settings[template]["active"] for template in ("A", "B", "C")
            ):
                self.notebook.select(0)
                self.change_world(
                    server_world=server_world,
                    world_in_title=_settings["world_in_title"],
                    settings=settings,
                )
                custom_error(
                    message='Ustaw pole "Powtarzaj ataki w odstępach [min]".',
                    parent=self.master,
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
                self.notebook.select(3)
                custom_error(
                    message='Ustaw pole "Sprawdzaj kurs co [min]".', parent=self.master
                )
                on_func_stop()
                return
            # Check incoming attacks sleep time
            if (
                _settings["notifications"]["check_incoming_attacks_sleep_time"] == 0
                and _settings["notifications"]["check_incoming_attacks"]
            ):
                self.change_world(
                    server_world=server_world,
                    world_in_title=_settings["world_in_title"],
                    settings=settings,
                )
                self.notebook.select(5)
                custom_error(
                    message='Ustaw pole "Twórz etykiety ataków co [min]".',
                    parent=self.master,
                )
                on_func_stop()
                return

        self.to_do = []

        incoming_attacks = False
        logged = False

        # Add functions into to_do list
        for server_world in self.settings_by_worlds:  # server_world = de199, pl173 etc.
            _settings = self.settings_by_worlds[server_world]
            _settings["temp"] = {
                "main_window": self,
                "to_do": self.to_do,
                "captcha_counter": self.captcha_counter,
            }
            to_do = []
            # Add daily bonus check
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
            if "mine_coin" in _settings and _settings["mine_coin"]:
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

        # Open browser if not already opend
        if not self.driver:
            self.driver = app_functions.run_driver(settings=settings)

        # Grid and set timer in custombar
        self.title_timer.grid(row=0, column=2, padx=5)
        self.time.set("Running..")

        # Główna pętla
        while self.running:
            if not self.to_do:
                self.running = False
                self.time.set("")
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

                    if not app_functions.paid(str(self.user_data["active_until"])):
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
                        if not app_functions.paid(str(self.user_data["active_until"])):
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
                except BaseException:
                    app_functions.log_error(self.driver)

            if not self.running:
                break
            if not self.to_do:
                continue

            self.time.set("Running..")

            _settings = self.to_do[0]["settings"]

            # Deleguję zadania na podstawie dopasowań self.to_do[0]["func"]
            try:
                if not logged:
                    logged = app_functions.log_in(self.driver, _settings)

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
                        ]["check_incoming_attacks_sleep_time"] * random.uniform(58, 62)
                        self.to_do[0]["errors_number"] = 0
                        self.to_do.append(self.to_do[0])

                    case "daily_bonus":
                        bot_functions.open_daily_bonus(self.driver, _settings)
                        current_time = datetime.today()
                        sec_to_midnight = (
                            (23 - current_time.hour) * 3600
                            + (59 - current_time.minute) * 60
                            + (59 - current_time.second)
                            + 2
                        )
                        self.to_do[0]["start_time"] = time.time() + sec_to_midnight
                        self.to_do[0]["errors_number"] = 0
                        self.to_do.append(self.to_do[0])

                    case "gathering":
                        incoming_attacks = False
                        if _settings["gathering"]["stop_if_incoming_attacks"]:
                            incoming_attacks = bot_functions.attacks_labels(
                                self.driver, _settings
                            )
                        if not _settings["gathering"]["stop_if_incoming_attacks"] or (
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
                        bot_functions.mine_coin(driver=self.driver)
                        self.to_do[0]["start_time"] = time.time() + 5 * random.uniform(
                            50, 70
                        )
                        self.to_do[0]["errors_number"] = 0
                        self.to_do.append(self.to_do[0])

                    case "premium_exchange":
                        bot_functions.premium_exchange(self.driver, _settings)
                        self.to_do[0]["start_time"] = time.time() + _settings["market"][
                            "check_every"
                        ] * random.uniform(50, 70)
                        self.to_do[0]["errors_number"] = 0
                        self.to_do.append(self.to_do[0])

                    case "send_troops":
                        (
                            send_number_times,
                            attacks_to_repeat,
                        ) = bot_functions.send_troops(self.driver, _settings)

                        # Clean from _settings and self.to_do
                        del _settings["scheduler"]["ready_schedule"][
                            0:send_number_times
                        ]

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
            except NoSuchWindowException:
                logger.error("NoSuchWindowException", exc_info=True)
                self.driver.switch_to.window(self.driver.window_handles[0])
                logged = app_functions.log_in(self.driver, _settings)
                continue
            except BaseException as e:
                # WebDriverException
                if "chrome not reachable" in str(e):
                    logger.error("Chrome is not reachable error", exc_info=True)
                    subprocess.run(
                        "taskkill /IM chromedriver.exe /F /T",
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    self.driver = app_functions.run_driver(settings=settings)
                    logged = app_functions.log_in(self.driver, _settings)
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
                    if not logged:
                        continue
                # For all other funcs than send_troops
                if self.to_do[0]["errors_number"] > 9:
                    del self.to_do[0]
                    logged = log_out_when_free_time(_settings)
                    if not logged:
                        continue

                html = self.driver.page_source
                # If disconected/sesion expired
                if (
                    html.find("chat-disconnected") != -1
                    or "session_expired" in self.driver.current_url
                ):
                    logged = app_functions.log_in(self.driver, _settings)
                    if logged:
                        continue

                    self.driver.quit()
                    self.driver = app_functions.run_driver(settings=_settings)
                    logged = app_functions.log_in(self.driver, _settings)
                    continue

                # Deal with known things like popups, captcha etc.
                if app_functions.unwanted_page_content(self.driver, _settings, html):
                    continue

                # Unknown error
                self.driver.quit()
                self.driver = app_functions.run_driver(settings=_settings)
                logged = app_functions.log_in(self.driver, _settings)
                continue

            # Zamyka stronę plemion jeśli do następnej czynności pozostało więcej niż 5min
            logged = log_out_when_free_time(_settings)

        # Zapis ustawień gdy bot zostanie ręcznie zatrzymany
        self.time.set("")
        self.title_timer.grid_remove()
        self.run_button.config(text="Uruchom")

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

            master = TopLevel(title_text="Tribal Wars Bot")

            ttk.Label(master.content_frame, text="Wybierz serwer i numer świata").grid(
                row=0, column=0, columnspan=2, padx=5, pady=(5, 0)
            )

            game_url_var = tk.StringVar()
            game_url = ttk.Combobox(
                master=master.content_frame,
                textvariable=game_url_var,
                state="readonly",
                justify="center",
                width=20,
            )
            game_url.grid(row=1, column=0, padx=5, pady=(5))
            game_url.set("Wybierz serwer")
            game_url["values"] = [
                "plemiona.pl",
                "die-staemme.de",
                "staemme.ch",
                "tribalwars.net",
                "tribalwars.nl",
                "tribalwars.se",
                "tribalwars.com.br",
                "tribalwars.com.pt",
                "divokekmeny.cz",
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

            world_number = tk.StringVar()
            world_number_input = ttk.Entry(
                master.content_frame,
                textvariable=world_number,
                width=5,
                justify="center",
            )
            world_number_input.grid(row=1, column=1, padx=(0, 5), pady=(5), sticky="E")

            def on_add_new_world() -> None:
                if not world_number.get().isnumeric():
                    custom_error(
                        "Numer świata powinien składać się z samych cyfr.",
                        parent=master,
                    )
                    return
                if self.add_new_world(
                    settings=settings,
                    game_url=game_url_var.get(),
                    world_number=world_number.get(),
                ):
                    master.destroy()
                else:
                    custom_error(
                        "Błąd. Upewnij się, że taki świat nadal istnieje.",
                        parent=master,
                    )

            add_button = ttk.Button(
                master.content_frame, text="Dodaj", command=on_add_new_world
            )
            add_button.grid(
                row=2, column=0, columnspan=2, padx=5, pady=(15, 5), sticky=ttk.EW
            )

            master.bind(
                "<Return>",
                lambda _: [
                    world_number_input.event_generate("<Leave>"),
                    add_button.event_generate("<Button-1>"),
                    on_add_new_world(),
                ],
            )
            center(window=master, parent=self.master)
            master.attributes("-alpha", 1.0)

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
            if server_world in self.settings_by_worlds:
                del self.settings_by_worlds[server_world]

            self.master.unbind("<Button-1>", self.btn_func_id)
            self.world_chooser_window.destroy()

        def on_leave(event: tk.Event) -> None:
            if event.widget != self.world_chooser_window:
                return

            def on_enter(event: tk.Event) -> None:
                if event.widget != self.world_chooser_window:
                    return
                self.master.unbind("<Button-1>", self.btn_func_id)

            def quit(event: tk.Event) -> None:
                self.master.unbind("<Button-1>", self.btn_func_id)
                self.world_chooser_window.destroy()

            self.btn_func_id = self.master.bind("<Button-1>", quit, "+")
            self.world_chooser_window.bind("<Enter>", on_enter)

        self.world_chooser_window = ttk.Toplevel(
            self.title_world, borderwidth=2, relief="groove"
        )
        self.world_chooser_window.attributes("-alpha", 0.0)
        self.world_chooser_window.overrideredirect(True)
        self.world_chooser_window.attributes("-topmost", 1)

        if not self.settings_by_worlds and "server_world" in settings:
            save_entry_to_settings(entries=self.entries_content, settings=settings)
            if settings["server_world"] not in self.settings_by_worlds:
                self.settings_by_worlds[settings["server_world"]] = deepcopy(settings)

        for index, server_world in enumerate(self.settings_by_worlds):
            country_code = re.search(r"\D+", server_world).group()
            world_in_title = server_world.replace(country_code, country_code.upper())
            ttk.Button(
                self.world_chooser_window,
                bootstyle="primary.Link.TButton",
                text=f"{world_in_title}",
                command=partial(
                    self.change_world, server_world, world_in_title, settings
                ),
            ).grid(row=index * 2, column=0, sticky=ttk.NSEW)

            ttk.Button(
                self.world_chooser_window,
                style="danger.primary.Link.TButton",
                image=self.images.exit,
                command=partial(delete_world, server_world),
            ).grid(row=index * 2, column=2, sticky=ttk.NSEW)

            ttk.Separator(self.world_chooser_window, style="default.TSeparator").grid(
                row=index * 2 + 1, column=0, columnspan=3, sticky=ttk.EW
            )

        ttk.Separator(
            self.world_chooser_window,
            orient=ttk.VERTICAL,
            style="default.TSeparator",
        ).grid(
            row=0, rowspan=len(self.settings_by_worlds) * 2 - 1, column=1, sticky=ttk.NS
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
            columnspan=3,
            sticky=ttk.NSEW,
        )

        self.world_chooser_window.bind("<Leave>", on_leave)
        center(self.world_chooser_window, self.title_world)
        self.world_chooser_window.attributes("-alpha", 1.0)


class JobsToDoWindow:

    translate = {
        "gathering": "zbieractwo",
        "auto_farm": "farmienie",
        "check_incoming_attacks": "etykiety ataków",
        "premium_exchange": "giełda premium",
        "send_troops": "planer",
        "mine_coin": "wybijanie monet",
        "daily_bonus": "bonus dzienny",
    }

    def __init__(self, main_window: MainWindow) -> None:
        self.master = TopLevel(title_text="Lista zadań", timer=main_window.time)

        self.content_frame = self.master.content_frame

        self.coldata = [
            {"text": "Świat", "stretch": False},
            "Zadanie",
            {"text": "Data wykonania", "stretch": False},
        ]

        rowdata = [
            tuple(
                (
                    row["server_world"],
                    self.translate[row["func"]],
                    time.strftime(
                        "%H:%M:%S %d.%m.%Y", time.localtime(row["start_time"])
                    ),
                )
            )
            for row in main_window.to_do
        ]

        self.table = Tableview(
            master=self.content_frame,
            coldata=self.coldata,
            rowdata=rowdata,
            datasource=main_window.to_do,
            paginated=True,
            searchable=True,
            stripecolor=("gray14", None),
        )
        self.table.grid(row=0, column=0)

        center(self.master, main_window.master)
        self.master.attributes("-alpha", 1.0)

    def update_table(self, main_window: MainWindow) -> None:
        rowdata = [
            tuple(
                (
                    row["server_world"],
                    self.translate[row["func"]],
                    time.strftime(
                        "%H:%M:%S %d.%m.%Y", time.localtime(row["start_time"])
                    ),
                )
            )
            for row in main_window.to_do
        ]
        self.table.build_table_data(coldata=self.coldata, rowdata=rowdata)


class PaymentWindow:
    def __init__(self, parent: MainWindow) -> None:
        self.master = TopLevel(title_text="Tribal Wars Bot")
        self.master.geometry("555x505")

        self.text = ttk.Text(
            master=self.master.content_frame,
            wrap="word",
        )
        self.text.grid(row=0, column=0, sticky=ttk.NSEW)
        self.text.insert("1.0", "Dostępne pakiety:\n", "bold_text")
        self.text.insert("2.0", "- 30zł za jeden miesiąc\n")
        self.text.insert("3.0", "- 55zł za dwa miesiące 60zł oszczędzasz 5zł\n")
        self.text.insert("4.0", "- 75zł za trzy miesiące 90zł oszczędzasz 15zł\n")
        self.text.insert("5.0", "Dostępne metody płatności:\n", "bold_text")
        self.text.insert(
            "6.0", "- blik na numer: 511 163 955 (nazwa odbiorcy: Klemens)\n"
        )
        self.text.insert(
            "7.0", "- przelew na numer: 95 1050 1025 1000 0097 5211 9777\n"
        )
        self.text.insert(
            "8.0",
            f'W tytule blika/przelewu należy wpisać swój login "{parent.user_data["user_name"]}"\n',
            "bold_text",
        )
        self.text.insert("9.0", "Czas oczekiwania:\n", "bold_text")
        self.text.insert("10.0", "Blik\n", "bold_text")
        self.text.insert("11.0", "- przeważnie w ciągu kilku godzin\n")
        self.text.insert("12.0", "- maksymalnie jeden dzień\n")
        self.text.insert("13.0", "Przelew\n", "bold_text")
        self.text.insert("14.0", "- przeważnie w ciągu jednego dnia *\n")
        self.text.insert(
            "15.0",
            "* Wyjątek stanowią weekendy i dni ustawowo wolne od pracy jako, że w te dni "
            "banki nie realizują przelewów. W takim przypadku w celu przyspieszenia aktywacji "
            "wystarczy wysłać potwierdzenie przelewu na adres e-mail k.spec@tuta.io. "
            "Na tej podstawie mogę dokonać aktywacji konta niezwłocznie po odczytaniu wiadomości.",
        )

        self.copy_icon = tk.PhotoImage(file="icons//copy.png")

        def copy_acc_number() -> None:
            self.text.clipboard_clear()
            self.text.clipboard_append("95 1050 1025 1000 0097 5211 9777")
            self.text.config(state="normal")
            self.text.insert("7.end", "skopiowano do schowka")
            self.text.config(state="disabled")

            def delete_extra_text() -> None:
                self.text.config(state="normal")
                self.text.delete("7.53", "7.end")
                self.text.config(state="disabled")

            self.text.after(ms=3000, func=delete_extra_text)

        copy_button = ttk.Button(
            master=self.text,
            image=self.copy_icon,
            style="copy.primary.Link.TButton",
            command=copy_acc_number,
        )
        copy_button.bind("<Enter>", lambda _: self.text.config(cursor=""))
        copy_button.bind("<Leave>", lambda _: self.text.config(cursor="xterm"))
        self.text.window_create("7.end", window=copy_button, padx=4)

        self.text.tag_add("account_number", "7.20", "8.0-1c")
        self.text.tag_add("italic_text", "15.0", "end")
        self.text.tag_add("indent_text", "1.0", "end")
        self.text.tag_add("first_line", "1.0", "1.end -1c")
        self.text.tag_add("last_line", "end -1 lines", "end")
        self.text.tag_add("strike", "3.23", "3.27", "4.24", "4.28")

        self.text.tag_config(
            "bold_text",
            font=("TkTextFont", 11, "bold"),
            lmargin1=16,
            spacing1=16,
            spacing3=3,
        )
        self.text.tag_config(
            "italic_text",
            font=("TkTextFont", 10, "italic"),
            lmargin1=16,
            lmargin2=25,
            spacing1=16,
        )
        self.text.tag_config("indent_text", lmargin1=25, rmargin=16)
        self.text.tag_config("first_line", spacing1=10)
        self.text.tag_config("last_line", spacing3=10)
        self.text.tag_config("strike", overstrike=True)

        self.text.tag_raise("bold_text", "indent_text")
        self.text.tag_raise("italic_text", "indent_text")

        self.text.config(state="disabled")

        center(window=self.master, parent=parent.master)
        self.master.attributes("-alpha", 1.0)


@log_errors()
def check_for_updates(
    force_update: bool = False,
    main_window: MainWindow = None,
    stable_release: bool = True,
) -> None:

    APP_NAME = "TribalWarsBot"
    APP_VERSION = "1.0.44"

    client = Client(ClientConfig())
    client.refresh()

    # Check for updates on stable channel
    if stable_release:
        app_update = client.update_check(APP_NAME, APP_VERSION)
    # Check for updates on any channel
    else:
        app_update = client.update_check(APP_NAME, APP_VERSION, strict=False)

    # Just check for available update do not process or update
    if not force_update:
        if app_update is not None:
            main_window.update_available = True
        return

    if app_update is not None:

        @log_errors()
        def clear_logs() -> None:
            if Path("logs").exists():
                open(Path(r"logs/log.txt"), "w").close()
            for file in os.listdir("logs"):
                if file.endswith(".png"):
                    Path(rf"logs/{file}").unlink(missing_ok=True)

        clear = threading.Thread(target=clear_logs, daemon=True)
        clear.start()

        def if_downloaded() -> None:
            if not app_update.is_downloaded():
                logger.debug("Downloading update..")
                master.after(250, if_downloaded)
                return
            progress_bar["value"] = 100
            description_progress_bar.config(text="Aktualizacja ukończona!")
            logger.debug("Downloaded file/patch")
            master.update_idletasks()
            master.after(500, master.destroy)
            logger.debug("Master destroyd")

        def print_status_info(info):
            percent_complete = int(float(info.get("percent_complete")))
            logger.debug(f"Downloaded in {percent_complete}%")
            progress_bar["value"] = percent_complete
            style.configure(
                "str_progress_in.Horizontal.TProgressbar", text=f"{percent_complete}%"
            )
            master.update_idletasks()

        master = tk.Tk()
        master.withdraw()

        style = ttk.Style(theme="darkly")
        configure_style(style=style)

        custom_error(
            message="Dostępna jest nowa aktualizacja!\n"
            "Po jej zakończeniu poczekaj cierpliwie aż aplikacja sama się uruchomi!"
        )

        update_window = TopLevel(title_text="TribalWarsBot")
        description_progress_bar = ttk.Label(
            update_window.content_frame,
            text="Aktualizowanie aplikacji. Proszę czekać..",
        )
        description_progress_bar.pack(anchor="center", pady=(0, 5))
        progress_bar = ttk.Progressbar(
            update_window.content_frame,
            orient="horizontal",
            mode="determinate",
            length=280,
            style="str_progress_in.Horizontal.TProgressbar",
        )
        progress_bar.pack(ipady=2, padx=5, pady=5)
        center(window=update_window)
        update_window.attributes("-alpha", 1.0)

        client.add_progress_hook(print_status_info)
        app_update.download(background=True)
        logger.debug("Started downloading in background")
        master.after(250, if_downloaded)
        master.mainloop()
        clear.join(timeout=5)
        app_update.extract_restart()


def configure_style(style: ttk.Style) -> None:
    # global font
    # style.configure("TLabel", font=("Courier New", 10))
    # style.configure("TEntry", font=("Courier New", 10))
    # style.configure("TCheckbutton", font=("Courier New", 10))
    # style.configure("TRadiobutton", font=("Courier New", 10))
    # style.configure("TButton", font=("Courier New", 10))

    # primary.TButton
    style.map(
        "TButton",
        bordercolor=[
            ("active", "#315172"),
            ("pressed", "#1f3247"),
            ("focus", "#315172"),
            ("disabled", "#383838"),
        ],
        background=[
            ("active", "#315172"),
            ("pressed", "#1f3247"),
            ("focus", "#315172"),
            ("disabled", "#383838"),
        ],
    )
    # primary.Link.TButton
    style.configure(
        "primary.Link.TButton",
        foreground="white",
        shiftrelief="",
    )
    style.map(
        "primary.Link.TButton",
        background=[("active", "gray24")],
        bordercolor=[("active", "gray50"), ("pressed", "gray50"), ("focus", "")],
        foreground=[("active", "white")],
        focuscolor=[("pressed", ""), ("focus", ""), ("active", "gray50")],
        shiftrelief=[("pressed", "")],
    )
    # danger.primary.Link.TButton
    style.configure("danger.primary.Link.TButton", foreground="white", padding=(6, 0))
    style.map(
        "danger.primary.Link.TButton",
        background=[("active", "#e74c3c")],
    )
    # copy.primary.Link.TButton
    style.configure(
        "copy.primary.Link.TButton",
        padding=(0, 0),
        background="#2f2f2f",
        bordercolor="#2f2f2f",
        lightcolor="#2f2f2f",
        darkcolor="#2f2f2f",
    )
    style.map(
        "copy.primary.Link.TButton",
        background=[("active", "gray24")],
        bordercolor=[
            ("alternate", "#2f2f2f"),
            ("active", "gray50"),
            ("pressed", "gray50"),
            ("focus", ""),
        ],
    )
    # default.TSeparator
    style.configure(
        "default.TSeparator",
        borderwidth=0,
    )
    # str_progress_in.Horizontal.TProgressbar
    style.layout(
        "str_progress_in.Horizontal.TProgressbar",
        [
            (
                "Horizontal.Progressbar.trough",
                {
                    "children": [
                        (
                            "Horizontal.Progressbar.pbar",
                            {"side": "left", "sticky": "ns"},
                        )
                    ],
                    "sticky": "nswe",
                },
            ),
            ("Horizontal.Progressbar.label", {"sticky": "nswe"}),
        ],
    )
    style.configure(
        "str_progress_in.Horizontal.TProgressbar",
        anchor="center",
        foreground="white",
    )
    # hide_or_show_password register_window
    style.configure(
        "pure.TButton", background="#2f2f2f", bordercolor="", padding=(4, 2)
    )
    style.map(
        "pure.TButton",
        background=[("active", "#2f2f2f")],
    )
    # padded frames
    style.configure("padded.TFrame", padding=[5, 15, 5, 15])


def periodically_check_for_updates(main_window: MainWindow) -> None:
    if hasattr(main_window, "update_available"):
        if main_window.update_available:
            return
    else:
        main_window.update_available = False
    check_update_thread = threading.Thread(
        target=lambda: check_for_updates(main_window=main_window), daemon=True
    )
    check_update_thread.start()
    thread_monitor(check_update_thread, main_window)
    main_window.master.after(
        ms=7_200_000,
        func=lambda: periodically_check_for_updates(main_window=main_window),
    )


def thread_monitor(thread: threading.Thread, main_window: MainWindow) -> None:
    if thread.is_alive():
        main_window.master.after(500, lambda: thread_monitor(thread, main_window))
        return
    if main_window.update_available:
        ToastNotification(
            title="TribalWarsBot Update",
            message=f"Dostępna jest nowa wersja aplikacji. ",
            topmost=True,
            bootstyle="primary",
        ).show_toast()


def main() -> None:
    driver = None
    settings = app_functions.load_settings()

    # Check for updates
    if hasattr(sys, "frozen"):
        if "stable_release" not in settings:
            settings["stable_release"] = True
        if settings["stable_release"]:
            check_for_updates(force_update=True)
        else:
            check_for_updates(force_update=True, stable_release=False)

    if settings["first_lunch"]:
        app_functions.first_app_lunch(settings=settings)

    root = tk.Tk()
    root.config(bg="white")
    root.withdraw()

    style = ttk.Style(theme="darkly")

    configure_style(style=style)

    main_window = MainWindow(master=root, driver=driver, settings=settings)
    LogInWindow(main_window=main_window, settings=settings)

    root.after(
        ms=7_200_000,
        func=lambda: periodically_check_for_updates(main_window=main_window),
    )

    main_window.master.mainloop()


if __name__ == "__main__":

    main()
