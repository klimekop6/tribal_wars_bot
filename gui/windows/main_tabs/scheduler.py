import json
import random
import time
import tkinter as tk
from datetime import datetime, timedelta
from functools import partial
from math import sqrt
from typing import TYPE_CHECKING, NamedTuple

import requests
import ttkbootstrap as ttk
import xmltodict
from ttkbootstrap import localization
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.validation import add_validation

from app.config import PYTHON_ANYWHERE_WORLD_SETTINGS
from app.constants import TROOPS, TROOPS_DEFF, TROOPS_OFF, TROOPS_SPEED
from app.decorators import log_errors
from app.functions import get_villages_id
from gui.functions import center, change_state, custom_error, forget_row, is_int
from gui.widgets.my_widgets import ScrollableFrame, TopLevel
from gui.windows.new_world import gmt_time_offset

if TYPE_CHECKING:
    from gui.windows.main import MainWindow

translate = localization.MessageCatalog.translate


class Scheduler(ScrollableFrame):
    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ) -> None:

        super().__init__(parent, padding=[0, 0, 11, 0], autohide=False)
        self.columnconfigure((0, 1), weight=1)

        self.entries_content = entries_content
        self.main_window = main_window

        entries_content["scheduler"] = {}

        add_int_validation = partial(
            add_validation,
            func=is_int,
            parent=self,
        )

        # Frame for text widgets
        text_widget_frame = ttk.Frame(self)
        text_widget_frame.grid(row=1, column=0, columnspan=2, sticky=ttk.NSEW)
        text_widget_frame.columnconfigure((0, 1), weight=1)

        # Text widgets
        self.start_villages = ttk.Label(
            text_widget_frame, text=translate("Starting villages")
        )
        self.start_villages.grid(row=0, column=0, pady=(0, 10))
        self.target_villages = ttk.Label(
            text_widget_frame, text=translate("Target villages")
        )
        self.target_villages.grid(row=0, column=1, pady=(0, 10))

        def clear_hint(text_widget: ttk.Text) -> None:
            if text_widget.get("1.0", "1.11") == translate("Coordinates"):
                text_widget.delete("1.0", "end")

        def text_hint(text_widget: ttk.Text) -> None:
            text_widget.insert(
                "1.0",
                translate(
                    "Coordinates of villages in XXX|YYY format "
                    "separated by space, tab or enter."
                ),
            )

        def text_mouse_scroll(text_widget: ttk.Text) -> None:
            def text_exceed(event=None) -> None:
                if text_widget.yview() != (0.0, 1.0):
                    text_widget.unbind("<MouseWheel>")
                    return
                text_widget.bind("<MouseWheel>", self._on_mousewheel)

            text_exceed()
            text_widget.bind("<Key>", lambda event: text_widget.after(25, text_exceed))
            text_widget.bind(
                "<<Paste>>", lambda event: text_widget.after(50, text_exceed), add="+"
            )

        def split_text(event=None) -> None:
            """Split to new rows if text is to long -> speedup tkinter Text widget"""

            try:
                clipboard_text: str = main_window.master.clipboard_get()
            except ttk.TclError:
                return
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
        self.villages_to_use = ttk.Text(
            text_widget_frame, wrap="word", height=5, width=28
        )
        self.villages_to_use.grid(
            row=1, column=0, padx=(10, 5), pady=(0, 5), sticky=ttk.EW
        )
        self.villages_to_use.bind("<<Paste>>", split_text)
        self.villages_to_use.bind(
            "<Enter>", lambda event: text_mouse_scroll(self.villages_to_use)
        )
        self.villages_to_use.bind(
            "<Button>", lambda event: clear_hint(self.villages_to_use)
        )

        # Wioski docelowe
        self.villages_destiny = ttk.Text(
            text_widget_frame, wrap="word", height=5, width=28
        )
        self.villages_destiny.grid(
            row=1, column=1, padx=(5, 10), pady=(0, 5), sticky=ttk.EW
        )
        self.villages_destiny.bind("<<Paste>>", split_text)
        self.villages_destiny.bind(
            "<Enter>", lambda event: text_mouse_scroll(self.villages_destiny)
        )
        self.villages_destiny.bind(
            "<Button>", lambda event: clear_hint(self.villages_destiny)
        )

        text_hint(self.villages_to_use)
        text_hint(self.villages_destiny)

        # Date entry settings
        ttk.Label(self, text=translate("Entry date of troops")).grid(
            row=2, column=0, columnspan=2, padx=10, pady=(15, 5), sticky=ttk.W
        )

        date_frame = ttk.Frame(self)
        date_frame.grid(row=3, column=0, columnspan=2, pady=(5, 0), sticky=ttk.EW)

        ttk.Label(date_frame, text=translate("From:")).grid(
            row=0, column=0, pady=5, padx=(30, 5)
        )
        ttk.Label(date_frame, text=translate("Until:")).grid(
            row=1, column=0, pady=5, padx=(30, 5)
        )

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

        # Rodzaj komendy -> atak lub wsparcie
        self.command_type_label = ttk.Label(self, text=translate("Command type"))
        self.command_type_label.grid(
            row=5, column=0, columnspan=2, padx=10, pady=(10, 5), sticky=ttk.W
        )
        self.command_type = ttk.StringVar()
        self.command_type_attack = ttk.Radiobutton(
            self,
            text=translate("Attack"),
            value="target_attack",
            variable=self.command_type,
        )
        self.command_type_attack.grid(
            row=6, column=0, padx=(30, 5), pady=5, sticky=ttk.W
        )
        self.command_type_support = ttk.Radiobutton(
            self,
            text=translate("Support"),
            value="target_support",
            variable=self.command_type,
        )
        self.command_type_support.grid(
            row=7, column=0, padx=(30, 5), pady=5, sticky=ttk.W
        )

        # Szablon wojsk
        self.template_label = ttk.Label(self, text=translate("Army template"))
        self.template_label.grid(row=8, column=0, padx=10, pady=(10, 5), sticky=ttk.W)

        # Wyślij wszystkie
        # region

        self.template_type = ttk.StringVar()

        def all_troops_radiobutton_command() -> None:
            # send_all
            self.choose_slowest_troop.config(state="readonly")
            self.choose_catapult_target.config(state="readonly")
            self.choose_catapult_target.set("Default")
            self.all_troops.event_generate("<Button-1>")

            # send_fake
            self.choosed_fake_template.set("")
            for widget in self.content_grid_slaves():
                if 19 < widget.grid_info()["row"] < 41:
                    if "TRadiobutton" in widget.winfo_class():
                        widget.event_generate("<Button-1>")
                        break

            # own_template
            self.army_frame.grid_slaves(row=0, column=1)[0].event_generate("<Button-1>")
            if self.repeat_attack.get():
                self.repeat_attack_checkbutton.invoke()
            change_state([self.army_frame, attacks_number_frame], True)
            forget_row(self, row_number=43)

        self.all_troops = ttk.Radiobutton(
            self,
            text=translate("Send all"),
            value="send_all",
            variable=self.template_type,
            command=all_troops_radiobutton_command,
        )
        self.all_troops.grid(
            row=9, column=0, columnspan=2, padx=(30, 5), pady=5, sticky=ttk.W
        )

        def only_off_or_deff() -> None:
            if self.template_type.get() == "send_all":
                return
            self.all_troops.invoke()

        self.army_type = ttk.StringVar()  # Wysłać jednostki off czy deff
        self.only_off_radiobutton = ttk.Radiobutton(
            self,
            text=translate("Send only offensive troops"),
            value="only_off",
            variable=self.army_type,
            command=only_off_or_deff,
        )
        self.only_off_radiobutton.grid(
            row=14, column=0, columnspan=2, padx=(50, 5), pady=5, sticky=ttk.W
        )
        self.settings_off_troops = ttk.Button(
            self,
            image=main_window.images.settings_sm,
            bootstyle="primary.Link.TButton",
            command=lambda: self.TroopsWindow(self, TROOPS_OFF, "off", settings)
            # image_on_hover=main_window.images.settings_hover_sm,
        )
        self.settings_off_troops.grid(
            row=14, column=0, columnspan=2, padx=(0, 25), sticky=ttk.E
        )

        self.only_deff_radiobutton = ttk.Radiobutton(
            self,
            text=translate("Send only deffensive troops"),
            value="only_deff",
            variable=self.army_type,
            command=only_off_or_deff,
        )
        self.only_deff_radiobutton.grid(
            row=15, column=0, columnspan=2, padx=(50, 5), pady=5, sticky=ttk.W
        )
        self.settings_deff_troops = ttk.Button(
            self,
            image=main_window.images.settings_sm,
            bootstyle="primary.Link.TButton",
            command=lambda: self.TroopsWindow(self, TROOPS_DEFF, "deff", settings)
            # image_on_hover=main_window.images.settings_hover_sm,
        )
        self.settings_deff_troops.grid(
            row=15, column=0, columnspan=2, padx=(0, 25), sticky=ttk.E
        )

        def send_snob_or_not(snob: bool) -> None:
            if self.template_type.get() != "send_all":
                self.all_troops.invoke()
            change_state(
                [self.snob_amount_entry, self.first_snob_army_size_entry], not snob
            )
            if snob:
                self.slowest_troop.set(translate("Nobleman")),
                self.choose_slowest_troop.configure(state="disabled")
            else:
                self.slowest_troop.set(translate("Ram"))
                self.choose_slowest_troop.configure(state="readonly")

        self.send_snob = ttk.StringVar()  # Czy wysłać szlachtę
        self.no_snob = ttk.Radiobutton(
            self,
            text=translate("Don't send noblemans"),
            value="no_snob",
            variable=self.send_snob,
            command=lambda: send_snob_or_not(False),
        )
        self.no_snob.grid(
            row=10, column=0, columnspan=2, padx=(50, 5), pady=5, sticky=ttk.W
        )

        self.snob = ttk.Radiobutton(
            self,
            text=translate("Send noblemans"),
            value="send_snob",
            variable=self.send_snob,
            command=lambda: send_snob_or_not(True),
        )
        self.snob.grid(
            row=11, column=0, columnspan=2, padx=(50, 5), pady=5, sticky=ttk.W
        )

        ttk.Label(self, text=translate("Noblemans amount")).grid(
            row=12, column=0, columnspan=2, padx=(70, 5), pady=(5, 0), sticky=ttk.W
        )
        self.snob_amount = ttk.IntVar(value=1)
        self.snob_amount_entry = ttk.Entry(
            self,
            textvariable=self.snob_amount,
            width=4,
            justify=ttk.CENTER,
            state="disabled",
        )
        self.snob_amount_entry.grid(
            row=12, column=0, columnspan=2, padx=(5, 25), pady=(5, 0), sticky=ttk.E
        )
        add_int_validation(self.snob_amount_entry, default=1, min=1)

        ttk.Label(self, text=translate("Guardian of the first nobleman \[%]")).grid(
            row=13, column=0, columnspan=2, padx=(70, 5), pady=5, sticky=ttk.W
        )
        self.first_snob_army_size = (
            ttk.IntVar()
        )  # Wielkość obstawy pierwszego grubego wyrażona w %
        self.first_snob_army_size_entry = ttk.Entry(
            self,
            textvariable=self.first_snob_army_size,
            width=4,
            justify=ttk.CENTER,
            state="disabled",
        )
        self.first_snob_army_size_entry.grid(
            row=13, column=0, columnspan=2, padx=(5, 25), pady=5, sticky=ttk.E
        )
        add_int_validation(self.first_snob_army_size_entry)

        ttk.Label(self, text=translate("Slowest troop")).grid(
            row=16, column=0, columnspan=2, padx=(50, 5), pady=(10, 5), sticky=ttk.W
        )
        self.slowest_troop = ttk.StringVar()
        self.choose_slowest_troop = ttk.Combobox(
            self,
            textvariable=self.slowest_troop,
            width=14,
            justify=ttk.CENTER,
            state="disabled",
        )
        self.choose_slowest_troop.grid(
            row=16, column=0, columnspan=2, padx=(5, 25), pady=(10, 5), sticky=ttk.E
        )
        self.choose_slowest_troop["values"] = [
            key for key in main_window.troops_dictionary
        ]

        ttk.Label(self, text=translate("Catapult target")).grid(
            row=17, column=0, columnspan=2, padx=(50, 5), pady=(5, 10), sticky=ttk.W
        )
        self.catapult_target = ttk.StringVar(value="Default")
        self.choose_catapult_target = ttk.Combobox(
            self,
            textvariable=self.catapult_target,
            values=["Default"] + list(main_window.buildings),
            width=14,
            justify=ttk.CENTER,
            state="disabled",
        )
        self.choose_catapult_target.grid(
            row=17, column=0, columnspan=2, padx=(5, 25), pady=(5, 10), sticky=ttk.E
        )
        # endregion

        # Wyślij fejki
        # region
        def fake_troops_radiobutton_command() -> None:
            # send_all
            self.send_snob.set("")
            self.snob.event_generate("<Button-1>")
            change_state(
                [self.snob_amount_entry, self.first_snob_army_size_entry], True
            )
            self.army_type.set("")
            self.slowest_troop.set("")
            self.choose_slowest_troop.config(state="disabled")

            # fake_troops
            self.fake_troops.event_generate("<Button-1>")

            # own_template
            self.army_frame.grid_slaves(row=0, column=1)[0].event_generate("<Button-1>")
            if self.repeat_attack.get():
                self.repeat_attack_checkbutton.invoke()
            change_state([self.army_frame, attacks_number_frame], True)
            self.choose_catapult_target.config(state="disabled")
            forget_row(self, row_number=43)

        self.fake_troops = ttk.Radiobutton(
            self,
            text=translate("Send fakes"),
            value="send_fake",
            variable=self.template_type,
            command=fake_troops_radiobutton_command,
        )
        self.fake_troops.grid(
            row=18, column=0, columnspan=2, padx=(30, 5), pady=5, sticky=ttk.W
        )

        ttk.Label(self, text=translate("Available fake templates")).grid(
            row=19, column=0, columnspan=2, padx=(50, 5), pady=5, sticky=ttk.W
        )

        settings.setdefault("scheduler", {})
        settings["scheduler"].setdefault("fake_templates", {})
        self.choosed_fake_template = ttk.StringVar()  # Wybrany szablon
        self.available_templates(
            settings=settings
        )  # Wyświetla dostępne szablony stworzone przez użytkownika

        ttk.Button(
            self,
            image=main_window.images.plus,
            bootstyle="primary.Link.TButton",
            command=lambda: self.create_template(settings=settings),
        ).grid(row=19, column=0, columnspan=2, padx=(0, 25), pady=5, sticky=ttk.E)

        # endregion

        # Własny szablon
        # region

        def on_catapult_value_change(*args) -> None:
            if (
                not self.choose_catapult_target2.winfo_ismapped()
                and self.troops["catapult"].get()
            ):
                ttk.Label(self, text=translate("Catapult target")).grid(
                    row=43,
                    column=0,
                    columnspan=2,
                    padx=(45, 5),
                    pady=(15, 0),
                    sticky=ttk.W,
                )
                self.choose_catapult_target2.grid(
                    row=43,
                    column=0,
                    columnspan=2,
                    padx=(5, 30),
                    pady=(15, 0),
                    sticky=ttk.E,
                )
                return
            if (
                self.choose_catapult_target2.winfo_ismapped()
                and not self.troops["catapult"].get()
            ):
                forget_row(self, row_number=43)

        def own_template_radiobutton_func() -> None:
            """self.own_template function"""
            # send_all
            self.send_snob.set("")
            self.snob.event_generate("<Button-1>")
            change_state(
                [self.snob_amount_entry, self.first_snob_army_size_entry], True
            )
            self.army_type.set("")
            self.slowest_troop.set("")
            self.choose_slowest_troop.config(state="disabled")

            # send_fake
            self.choosed_fake_template.set("")
            for widget in self.content_grid_slaves():
                if 19 < widget.grid_info()["row"] < 41:
                    if "TRadiobutton" in widget.winfo_class():
                        widget.event_generate("<Button-1>")
                        break

            # own_template
            self.own_template.event_generate("<Button-1>")
            self.split_attacks_number.set("1")
            self.split_attacks.event_generate("<FocusOut>")
            change_state([self.army_frame, attacks_number_frame], False)
            self.choose_catapult_target.config(state="disabled")
            on_catapult_value_change()

        button_info_frame = ttk.Frame(self)
        button_info_frame.grid(
            row=41, column=0, columnspan=2, padx=(30, 5), pady=(15, 10), sticky=ttk.W
        )

        self.own_template = ttk.Radiobutton(
            button_info_frame,
            text=translate("Own template"),
            value="send_my_template",
            variable=self.template_type,
            command=own_template_radiobutton_func,
        )
        self.own_template.grid(row=0, column=0, sticky=ttk.W)

        info = ttk.Label(button_info_frame, image=main_window.images.question)
        info.grid(row=0, column=1, padx=(5, 0), sticky=ttk.W)

        ToolTip(
            info,
            text="W poniższych polach można podać konkretną liczbę jednostek do wysłania, "
            "wpisać słowo max lub formułę.\n\nPodanie konkretnej liczby np. 50 w komórce "
            "z lk oznacza wysłanie równo 50lk. Jeśli w wiosce taka ilość nie będzie dostępna "
            "to atak nie zostanie wysłany.\n\nSłowo max oznacza wybranie maksymalnej ilości "
            "jednostki danego typu dostępnej w wiosce w chwili wysyłania ataku/wsparcia. Dla "
            "ułatwienia można kliknąć w ikonę jednostki co w przypadku pustej komórki doda "
            "wartość max a w pozostałych przypadkach wyczyści ją.\n\nFormuła ma postać "
            "wyrażenia min-max.\n"
            "Przykładowo 50-250 oznacza minialmną ilość równą 50 i maksymalną równą 250. "
            "W takiej sytuacji możliwe są trzy scenariuesze:\n"
            "1. W wiosce znajduję się mniej niż 50 jednostek danego typu. Atak nie zostanie wysłany.\n"
            "2. W wiosce znajduję się liczba jednostek pomiędzy wartością min i max np. 150. "
            "Atak zostanie wysłany z aktualnie dostępną ilością (150) jednostek danego typu.\n"
            "3. W wiosce znajduję się więcej jednostek niż podana wartość max. Atak zostanie "
            "wysłany z maksymalną podaną ilością (250) jednostek danego typu.",
            wraplength=400,
            topmost=True,
        )

        self.army_frame = ttk.Frame(self)
        self.army_frame.grid(
            row=42, column=0, columnspan=2, padx=(0, 25), sticky=ttk.EW
        )

        self.army_frame.columnconfigure((tuple(range(8))), weight=1)

        def clear_or_set_max(label: ttk.Label, troop_entry: ttk.StringVar):
            if self.template_type.get() != "send_my_template":
                self.own_template.invoke()
            if troop_entry.get().strip():
                troop_entry.set("")
            else:
                troop_entry.set("max")

        spear_label = ttk.Label(
            self.army_frame,
            image=main_window.images.spear,
        )
        spear_label.grid(row=0, column=0, padx=(30, 8), pady=(5, 0), sticky=ttk.E)
        spear_label.bind(
            "<Button-1>", lambda _: clear_or_set_max(spear_label, self.troops["spear"])
        )

        spy_label = ttk.Label(self.army_frame, image=main_window.images.spy)
        spy_label.grid(row=0, column=2, padx=(24, 8), pady=(5, 0), sticky=ttk.E)
        spy_label.bind(
            "<Button-1>", lambda _: clear_or_set_max(spy_label, self.troops["spy"])
        )

        ram_label = ttk.Label(self.army_frame, image=main_window.images.ram)
        ram_label.grid(row=0, column=4, padx=(24, 8), pady=(5, 0), sticky=ttk.E)
        ram_label.bind(
            "<Button-1>", lambda _: clear_or_set_max(ram_label, self.troops["ram"])
        )

        knihgt_label = ttk.Label(self.army_frame, image=main_window.images.knight)
        knihgt_label.grid(row=0, column=6, padx=(24, 8), pady=(5, 0), sticky=ttk.E)
        knihgt_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(knihgt_label, self.troops["knight"]),
        )

        sword_label = ttk.Label(self.army_frame, image=main_window.images.sword)
        sword_label.grid(row=1, column=0, padx=(30, 8), pady=(5, 0), sticky=ttk.E)
        sword_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(sword_label, self.troops["sword"]),
        )

        light_label = ttk.Label(self.army_frame, image=main_window.images.light)
        light_label.grid(row=1, column=2, padx=(24, 8), pady=(5, 0), sticky=ttk.E)
        light_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(light_label, self.troops["light"]),
        )

        catapult_label = ttk.Label(self.army_frame, image=main_window.images.catapult)
        catapult_label.grid(row=1, column=4, padx=(24, 8), pady=(5, 0), sticky=ttk.E)
        catapult_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(catapult_label, self.troops["catapult"]),
        )

        snob_label = ttk.Label(self.army_frame, image=main_window.images.snob)
        snob_label.grid(row=1, column=6, padx=(24, 8), pady=(5, 0), sticky=ttk.E)
        snob_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(snob_label, self.troops["snob"]),
        )

        axe_label = ttk.Label(self.army_frame, image=main_window.images.axe)
        axe_label.grid(row=2, column=0, padx=(30, 8), pady=(5, 0), sticky=ttk.E)
        axe_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(axe_label, self.troops["axe"]),
        )

        marcher_label = ttk.Label(self.army_frame, image=main_window.images.marcher)
        marcher_label.grid(row=2, column=2, padx=(24, 8), pady=(5, 0), sticky=ttk.E)
        marcher_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(marcher_label, self.troops["marcher"]),
        )

        archer_label = ttk.Label(self.army_frame, image=main_window.images.archer)
        archer_label.grid(row=3, column=0, padx=(30, 8), pady=(5, 5), sticky=ttk.E)
        archer_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(archer_label, self.troops["archer"]),
        )

        heavy_label = ttk.Label(self.army_frame, image=main_window.images.heavy)
        heavy_label.grid(row=3, column=2, padx=(24, 8), pady=(5, 5), sticky=ttk.E)
        heavy_label.bind(
            "<Button-1>",
            lambda _: clear_or_set_max(heavy_label, self.troops["heavy"]),
        )

        self.troops = {
            troop: ttk.StringVar() for troop in main_window.troops_dictionary.values()
        }

        self.troops["catapult"].trace_add("write", on_catapult_value_change)

        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["spear"],
        ).grid(row=0, column=1, pady=(5, 0), sticky=ttk.EW)
        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["spy"],
        ).grid(row=0, column=3, pady=(5, 0), sticky=ttk.EW)
        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["ram"],
        ).grid(row=0, column=5, pady=(5, 0), sticky=ttk.EW)
        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["knight"],
        ).grid(row=0, column=7, pady=(5, 0), sticky=ttk.EW)
        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["sword"],
        ).grid(row=1, column=1, pady=(5, 0), sticky=ttk.EW)
        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["light"],
        ).grid(row=1, column=3, pady=(5, 0), sticky=ttk.EW)
        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["catapult"],
        ).grid(row=1, column=5, pady=(5, 0), sticky=ttk.EW)
        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["snob"],
        ).grid(row=1, column=7, pady=(5, 0), sticky=ttk.EW)
        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["axe"],
        ).grid(row=2, column=1, pady=(5, 0), sticky=ttk.EW)
        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["marcher"],
        ).grid(row=2, column=3, pady=(5, 0), sticky=ttk.EW)
        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["archer"],
        ).grid(row=3, column=1, pady=(5, 5), sticky=ttk.EW)
        ttk.Entry(
            self.army_frame,
            state="disabled",
            width=6,
            justify=ttk.CENTER,
            textvariable=self.troops["heavy"],
        ).grid(row=3, column=3, pady=(5, 5), sticky=ttk.EW)

        self.choose_catapult_target2 = ttk.Combobox(
            self,
            textvariable=self.catapult_target,
            values=["Default"] + list(main_window.buildings),
            state="readonly",
            width=14,
            justify=ttk.CENTER,
        )

        # Liczba ataków
        attacks_number_frame = ttk.Labelframe(
            self.army_frame, text=translate("Attacks amount"), labelanchor="n"
        )
        attacks_number_frame.grid(
            row=2,
            rowspan=2,
            column=5,
            columnspan=3,
            pady=(5, 5),
            sticky=ttk.NSEW,
        )
        attacks_number_frame.rowconfigure(0, weight=1)
        attacks_number_frame.columnconfigure(0, weight=1)
        self.split_attacks_number = ttk.IntVar(value=1)
        self.split_attacks = ttk.Entry(
            attacks_number_frame,
            width=5,
            state="disabled",
            justify=ttk.CENTER,
            textvariable=self.split_attacks_number,
        )
        self.split_attacks.grid(row=0, column=0)
        add_int_validation(self.split_attacks, default=1, min=1)

        settings["scheduler"].setdefault("ready_schedule", [])
        if settings["scheduler"]["ready_schedule"]:
            current_time = time.time()
            settings["scheduler"]["ready_schedule"] = [
                value
                for value in settings["scheduler"]["ready_schedule"]
                if value["send_time"] > current_time
            ]

        self.repeat_attack = ttk.BooleanVar()

        def repeat_attack_checkbutton_command() -> None:
            change_state(
                self.total_attacks_number_entry, self.repeat_attack.get(), reverse=True
            )
            if self.repeat_attack.get():
                if main_window.loading:
                    return
                self.own_template.invoke()

        self.repeat_attack_checkbutton = ttk.Checkbutton(
            self,
            text=translate("Repeat attack after its return"),
            variable=self.repeat_attack,
            onvalue=True,
            offvalue=False,
            command=repeat_attack_checkbutton_command,
        )
        self.repeat_attack_checkbutton.grid(
            row=44, columnspan=2, padx=(45, 0), pady=(20, 0), sticky=ttk.W
        )

        self.total_attacks_number = ttk.IntVar(value=1)
        self.total_attacks_number_label = ttk.Label(
            self, text=translate("Total number of repetitions")
        )
        self.total_attacks_number_label.grid(
            row=45, column=0, padx=(65, 0), pady=10, sticky=ttk.W
        )
        self.total_attacks_number_entry = ttk.Entry(
            self,
            textvariable=self.total_attacks_number,
            width=4,
            justify=ttk.CENTER,
            state="disabled",
        )
        self.total_attacks_number_entry.grid(
            row=45, columnspan=2, padx=(5, 30), pady=10, sticky=ttk.E
        )
        add_int_validation(self.total_attacks_number_entry, default=1, min=1)

        # endregion

        ttk.Separator(self, orient="horizontal").grid(
            row=46, column=0, columnspan=2, pady=(5, 0), sticky=("W", "E")
        )

        footer = ttk.Frame(self)
        footer.grid(row=47, column=0, columnspan=2, padx=10, pady=10, sticky=ttk.EW)
        footer.columnconfigure((0, 1), weight=1, uniform="footer")

        self.show_schedule = ttk.Button(
            footer,
            text=translate("Show schedule \[F4]"),
            command=lambda: self.show_existing_schedule(
                settings=settings, main_window=main_window
            ),
        )
        self.show_schedule.grid(row=0, column=0, padx=(0, 5), sticky=ttk.EW)

        self.add_to_schedule = ttk.Button(
            footer,
            text=translate("Add to schedule \[F5]"),
            command=lambda: self.create_schedule(
                settings=settings, main_window=main_window
            ),
        )
        self.add_to_schedule.grid(row=0, column=1, padx=(5, 0), sticky=ttk.EW)

        # Bindings

        self.bind_all("<F4>", lambda _: self.show_schedule.invoke())
        self.bind_all("<F5>", lambda _: self.add_to_schedule.invoke())

    def available_templates(self, settings: dict) -> None:
        def delete_template(row_number, fake_templates, template_name):
            if (
                template_name
                in self.main_window.settings_by_worlds[settings["server_world"]][
                    "scheduler"
                ]["fake_templates"]
            ):
                del self.main_window.settings_by_worlds[settings["server_world"]][
                    "scheduler"
                ]["fake_templates"][template_name]
            if template_name in fake_templates:
                del fake_templates[template_name]
            forget_row(self, row_number)
            if not fake_templates:
                self.available_templates(settings=settings)
            self.update_idletasks()

        fake_templates = settings["scheduler"]["fake_templates"]

        if not fake_templates:
            ttk.Label(self, text=translate("No templates available")).grid(
                row=20, column=0, columnspan=2, padx=(70, 5), pady=5, sticky=ttk.W
            )

        for index, template_name in enumerate(fake_templates):
            template_button = ttk.Radiobutton(
                self,
                text=f"{template_name}",
                value=fake_templates[template_name],
                variable=self.choosed_fake_template,
                command=lambda: self.fake_troops.invoke(),
            )
            template_button.grid(
                row=20 + index,
                column=0,
                columnspan=2,
                padx=(70, 5),
                sticky=ttk.W,
            )
            text = "\n".join(
                f'{troop["priority_number"]} {troop_name.upper()}  Min={troop["min_value"]}  '
                f'Max={troop["max_value"]}'
                for troop_name, troop in fake_templates[
                    list(fake_templates)[index]
                ].items()
            )
            ToolTip(template_button, text=text, topmost=True)
            ttk.Button(
                self,
                image=self.main_window.images.exit,
                style="danger.primary.Link.TButton",
                padding=(10, 5),
                command=partial(
                    delete_template, index + 20, fake_templates, template_name
                ),
            ).grid(
                row=20 + index,
                column=0,
                columnspan=2,
                padx=(5, 25),
                sticky=ttk.E,
            )

    @log_errors()
    def create_schedule(self, settings: dict, main_window: "MainWindow") -> None:
        """Create scheduled defined on used options by the user"""

        def local_custom_error(message, scroll_to_widget: tk.Widget = None) -> None:
            if scroll_to_widget:
                self.scroll_to_widget_top(scroll_to_widget)
            custom_error(message=message, parent=self.master)

        # Safeguards
        if self.villages_to_use.get(
            "1.0", "1.5"
        ) == "Współ" or self.villages_to_use.compare("end-1c", "==", "1.0"):
            self.villages_to_use.configure(highlightbackground="#e74c3c")
            local_custom_error("Brak wiosek startowych", self.start_villages)
            self.villages_to_use.bind(
                "<Button>",
                lambda _: self.villages_to_use.configure(highlightbackground="#555555"),
                add=True,
            )
            return

        if self.villages_destiny.get(
            "1.0", "1.5"
        ) == "Współ" or self.villages_destiny.compare("end-1c", "==", "1.0"):
            self.villages_destiny.configure(highlightbackground="#e74c3c")
            local_custom_error("Brak wiosek docelowych", self.target_villages)
            self.villages_destiny.bind(
                "<Button>",
                lambda _: self.villages_destiny.configure(
                    highlightbackground="#555555"
                ),
                add=True,
            )
            return

        if not self.command_type.get():
            self.on_invalid(self.command_type_attack, self.command_type_support)
            local_custom_error("Wybierz rodzaj komendy", self.command_type_label)
            return

        if not self.template_type.get():
            self.on_invalid(self.all_troops, self.fake_troops, self.own_template)
            local_custom_error("Wybierz szablon wojsk", self.template_label)
            return

        if "send_all" in self.template_type.get() and not self.send_snob.get():
            self.on_invalid(self.no_snob, self.snob)
            local_custom_error(
                "Wybierz czy atak powinien zawierać szlachtę", self.template_label
            )
            return

        if (
            "send_all" in self.template_type.get()
            and "send_snob" in self.send_snob.get()
            and not self.snob_amount.get()
        ):
            local_custom_error(
                "Liczba szlachiców musi być większa od zera", self.template_label
            )
            return

        if (
            "send_fake" in self.template_type.get()
            and not self.choosed_fake_template.get()
        ):
            self.on_invalid(
                *[
                    widget
                    for widget in self.content_grid_slaves()
                    if 19 < widget.grid_info()["row"] < 41
                    and "TRadiobutton" in widget.winfo_class()
                ]
            )
            local_custom_error("Wybierz szablon fejków do wysłania", self.fake_troops)
            return

        if (
            "send_my_template" in self.template_type.get()
            and not self.split_attacks_number.get()
        ):
            local_custom_error(
                "Liczba ataków powinna być większa od zera", self.own_template
            )
            return

        if "send_my_template" in self.template_type.get() and not any(
            troop_value.get().strip() for troop_value in self.troops.values()
        ):
            widgets = [
                widget
                for widget in self.army_frame.winfo_children()
                if "TEntry" in widget.winfo_class()
            ]
            for widget in widgets:
                widget.configure(bootstyle="danger")
                widget.bind(
                    "<Button-1>",
                    lambda _: [
                        [
                            widget.configure(bootstyle="default"),
                            widget.unbind("<Button-1>"),
                        ]
                        for widget in widgets
                    ],
                )
            local_custom_error(
                "Nie wybrano żadnych jednostek do wysłania", self.own_template
            )
            return

        if self.repeat_attack.get() and not self.total_attacks_number.get():
            local_custom_error(
                "Łączna liczba ataków powinna być większa od zera", self.own_template
            )
            return

        try:
            UNIT_SPEED_MODIFIER = 1 / (
                float(settings["world_config"]["speed"])
                * float(settings["world_config"]["unit_speed"])
            )
        except KeyError:
            try:
                response = requests.get(
                    f"{PYTHON_ANYWHERE_WORLD_SETTINGS}/{settings['server_world']}.xml"
                )
            except KeyError:
                custom_error(
                    message=translate(
                        "Error occured. Try add/switch world in case you have "
                        "recently delete one."
                    ),
                    parent=self.master,
                )
            if not response.ok:
                custom_error(
                    message=translate("Error occured. Try again!"), parent=self.master
                )
                return
            world_config = xmltodict.parse(response.content)
            settings["world_config"]["speed"] = world_config["config"]["speed"]
            settings["world_config"]["unit_speed"] = world_config["config"][
                "unit_speed"
            ]
            UNIT_SPEED_MODIFIER = 1 / (
                float(settings["world_config"]["speed"])
                * float(settings["world_config"]["unit_speed"])
            )

        # Base info
        sends_from = self.villages_to_use.get("1.0", ttk.END)
        sends_to = self.villages_destiny.get("1.0", ttk.END)
        command_type = self.command_type.get()
        template_type = self.template_type.get()

        # Timings
        try:
            TIME_DIFFRENCE = (
                datetime.utcoffset(datetime(2023, 1, 1).astimezone()).seconds
                - settings["world_config"]["gmt_time_offset"] * 3600
            )
        except KeyError:
            settings["world_config"]["gmt_time_offset"] = gmt_time_offset(
                settings["country_code"]
            )
            TIME_DIFFRENCE = (
                datetime.utcoffset(datetime(2023, 1, 1).astimezone()).seconds
                - settings["world_config"]["gmt_time_offset"] * 3600
            )
        time_change = False
        winter_time_change = datetime.strptime(
            "29.10.2023 02:59:59:000", "%d.%m.%Y %H:%M:%S:%f"
        ).timestamp()
        # summer_time_change

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
        if current_time < winter_time_change < final_arrival_time_in_sec:
            time_change = True
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
            # When night.start == 0 than skip to the begining of the next day
            if not night.start_hour:
                first_night_bonus_start += timedelta(days=1).total_seconds()
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
                if not night.start_hour:
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

        match template_type:
            case "send_all":

                def update_troops_to_include_or_exclude(army_type: str, troops: dict):
                    for troop, include in settings["scheduler"][
                        f"only_{army_type}_troops"
                    ].items():
                        if (
                            include
                            and troop not in troops
                            or troop in troops
                            and not troops[troop]
                        ):
                            troops_to_include.append(troop)
                        elif not include and troop in troops and troops[troop]:
                            troops_to_exclude.append(troop)

                army_type = self.army_type.get()
                troops_to_include = []
                troops_to_exclude = []
                if army_type == "only_off":
                    if "only_off_troops" in settings["scheduler"]:
                        update_troops_to_include_or_exclude("off", TROOPS_OFF)
                if army_type == "only_deff":
                    if "only_deff_troops" in settings["scheduler"]:
                        update_troops_to_include_or_exclude("deff", TROOPS_DEFF)
                send_snob = self.send_snob.get()
                if send_snob == "send_snob":
                    snob_amount = self.snob_amount.get()
                    first_snob_army_size = self.first_snob_army_size.get()
                slowest_troop = self.slowest_troop.get()
                slowest_troop = main_window.troops_dictionary[slowest_troop]
                army_speed = TROOPS_SPEED[slowest_troop] * UNIT_SPEED_MODIFIER
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
                army_speed = (
                    max(
                        TROOPS_SPEED[troop_name]
                        for troop_name, dict_info in sorted_choosed_fake_template
                        if dict_info["min_value"] > 0
                    )
                    * UNIT_SPEED_MODIFIER
                )

            case "send_my_template":
                troops = {}
                for troop_name, troop_value in self.troops.items():
                    troop_value = troop_value.get().strip()
                    if troop_value:
                        if troop_value.isnumeric() and int(troop_value) == 0:
                            continue
                        troops[troop_name] = troop_value
                army_speed = (
                    max(TROOPS_SPEED[troop_name] for troop_name in troops.keys())
                    * UNIT_SPEED_MODIFIER
                )
                if (
                    command_type == "target_support"
                    and "knight" in troops
                    and (troops["knight"] == "max" or int(troops["knight"]) > 0)
                ):
                    army_speed = 10 * UNIT_SPEED_MODIFIER
                split_attacks_number = self.split_attacks_number.get()
                catapult_target = self.catapult_target.get()
                if catapult_target != "Default":
                    for key, value in zip(
                        main_window.buildings._fields, main_window.buildings
                    ):
                        if value == catapult_target:
                            catapult_target = key
                repeat_attack = self.repeat_attack.get()
                total_attacks_number = self.total_attacks_number.get()

        villages = get_villages_id(settings=settings)

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
                villages = get_villages_id(
                    settings=settings, update=True
                )  # Update villages
                try:
                    send_from_village_id = villages[send_from][
                        :-1
                    ]  # It returns village ID
                except KeyError:
                    custom_error(
                        message=f"Wioska {send_from} nie istnieje.",
                        parent=self.master,
                    )
                    self.yview_moveto(0)
                    return
                try:
                    send_to_village_id = villages[send_to][:-1]  # It returns village ID
                except KeyError:
                    custom_error(
                        message=f"Wioska {send_to} nie istnieje.",
                        parent=self.master,
                    )
                    self.yview_moveto(0)
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
                    if army_type == "only_off" or army_type == "only_deff":
                        if troops_to_include:
                            send_info["troops_to_include"] = troops_to_include
                        if troops_to_exclude:
                            send_info["troops_to_exclude"] = troops_to_exclude

                    send_info["send_snob"] = send_snob
                    if send_snob == "send_snob":
                        send_info["snob_amount"] = snob_amount
                        send_info["first_snob_army_size"] = first_snob_army_size

                    send_info["slowest_troop"] = slowest_troop
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
                    current_command_final_arrival_time_in_sec
                    - travel_time_in_sec
                    + TIME_DIFFRENCE
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
                    arrival_time_in_sec - travel_time_in_sec + TIME_DIFFRENCE
                )  # sec since epoch

            if time_change:
                if (
                    send_info["send_time"]
                    < winter_time_change
                    < send_info["send_time"] + travel_time_in_sec
                ):
                    send_info["send_time"] + 3600

            if send_info["send_time"] - 3 < current_time:
                sends_from.append(send_from)
                continue

            send_info_list.append(send_info)

        if not send_info_list:
            custom_error(message="Termin wysyłki wojsk już minął", parent=self.master)
            self.yview_moveto(0)
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
        self.yview_moveto(0)
        self.villages_to_use.delete("1.0", ttk.END)
        self.villages_destiny.delete("1.0", ttk.END)

        custom_error(message="Dodano do planera!", auto_hide=True, parent=self.master)

    @log_errors()
    def create_template(self, settings: dict) -> None:
        """As named it creates fake template to use"""

        def add_to_template() -> None:

            nonlocal last_row_number, template

            if not template_name_entry.get().strip():
                self.on_invalid(template_name_entry)
                custom_error(
                    message=translate("Enter a name for the template"), parent=frame
                )
                return

            if translate("Choose") in choose_troop_type.get():
                choose_troop_type.configure(bootstyle="danger")
                custom_error(
                    message=translate("Choose unit from the list"), parent=frame
                )
                choose_troop_type.bind(
                    "<Button-1>",
                    lambda _: choose_troop_type.configure(bootstyle="default"),
                )
                return

            if int(max_value_entry.get()) <= 0:
                self.on_invalid(max_value_entry)
                custom_error(
                    message=translate("The maximum value must be greater than zero"),
                    parent=frame,
                )
                return

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

            troop = self.main_window.troops_dictionary[troop]

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

        template_name = ttk.StringVar()
        priority_number = ttk.IntVar(value=1)
        troop_type = ttk.StringVar(value=translate("Choose unit"))
        min_value = ttk.IntVar()
        max_value = ttk.IntVar()

        top_frame = ttk.Frame(frame)
        top_frame.grid(row=0, column=0, columnspan=5, padx=5, pady=(5, 10))
        top_frame.columnconfigure(0, weight=1)

        ttk.Label(
            top_frame,
            text=translate("Unit matching template"),
        ).grid(row=0, column=0, padx=5)

        info = ttk.Label(top_frame, image=self.main_window.images.question)
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

        ttk.Label(frame, text=translate("Template name:")).grid(
            row=1, column=0, columnspan=5, padx=10, pady=10, sticky=ttk.W
        )

        template_name_entry = ttk.Entry(frame, textvariable=template_name)
        template_name_entry.grid(
            row=1, column=0, columnspan=5, padx=10, pady=10, sticky=ttk.E
        )

        ttk.Label(frame, text=translate("Priority")).grid(row=2, column=0, padx=(10, 5))
        ttk.Label(frame, text=translate("Unit")).grid(row=2, column=1, padx=5)
        ttk.Label(frame, text="Min").grid(row=2, column=2, padx=5)
        ttk.Label(frame, text="Max").grid(row=2, column=3, padx=(5, 10))

        choose_priority_number = ttk.Combobox(
            frame, textvariable=priority_number, width=3, justify=ttk.CENTER
        )
        choose_priority_number.grid(row=3, column=0, padx=(10, 5), pady=(0, 5))
        choose_priority_number["state"] = "readonly"
        choose_priority_number["values"] = tuple(num for num in range(1, 10))

        choose_troop_type = ttk.Combobox(
            frame, textvariable=troop_type, width=16, justify=ttk.CENTER
        )
        choose_troop_type.grid(row=3, column=1, padx=5, pady=(0, 5))
        choose_troop_type["state"] = "readonly"
        choose_troop_type["values"] = [
            key for key in self.main_window.troops_dictionary
        ]

        ttk.Entry(frame, textvariable=min_value, width=4, justify=ttk.CENTER).grid(
            row=3, column=2, padx=5, pady=(0, 5)
        )
        max_value_entry = ttk.Entry(
            frame, textvariable=max_value, width=4, justify=ttk.CENTER
        )
        max_value_entry.grid(row=3, column=3, padx=(5, 10), pady=(0, 5))

        ttk.Button(
            frame,
            bootstyle="primary.Link.TButton",
            image=self.main_window.images.plus,
            command=add_to_template,
        ).grid(row=3, column=4, padx=(0, 10), pady=(0, 5))

        def create_template_button_command() -> None:
            if not any(template[troop]["min_value"] for troop in template):
                custom_error(
                    translate(
                        "At least one unit must have a minimum value greater than 0"
                    ),
                    parent=frame,
                )
                return
            fake_templates[template_name.get()] = template
            template_window.destroy(),
            self.redraw_availabe_templates(settings=settings)

        ttk.Button(
            frame,
            text=translate("Create template"),
            command=create_template_button_command,
        ).grid(row=50, column=0, columnspan=5, pady=(10, 10))

        center(template_window, self.master)
        template_window.attributes("-alpha", 1.0)

    def on_invalid(self, *widgets: tk.Widget) -> None:
        for widget in widgets:
            widget.configure(bootstyle="danger")
            widget.bind(
                "<Button-1>",
                lambda _: [widget.configure(bootstyle="default") for widget in widgets],
            )

    def redraw_availabe_templates(self, settings: dict) -> None:
        forget_row(self, rows_beetwen=(19, 40))
        self.available_templates(settings=settings)
        self.update_idletasks()

    def show_existing_schedule(self, settings: dict, main_window) -> None:
        if hasattr(self, "existing_schedule_window"):
            if self.existing_schedule_window.winfo_exists():
                return

        self.existing_schedule_window = TopLevel(title_text="Tribal Wars Bot")

        content_frame = self.existing_schedule_window.content_frame

        self.coldata = [
            {"text": translate("Send date"), "stretch": False, "anchor": "center"},
            {"text": translate("World"), "stretch": False, "anchor": "center"},
            {"text": translate("Command"), "stretch": False, "anchor": "center"},
            {"text": translate("Type"), "stretch": False, "anchor": "center"},
            {
                "text": translate("Starting village"),
                "stretch": False,
                "anchor": "center",
            },
            {
                "text": translate("Destination village"),
                "stretch": False,
                "anchor": "center",
            },
            {
                "text": translate("Entry date of troops"),
                "stretch": False,
                "anchor": "center",
            },
        ]

        schedule_translate = {
            "target_support": translate("support"),
            "target_attack": translate("attack"),
            "send_all": translate("send all"),
            "send_fake": translate("send fake"),
            "send_my_template": translate("own template"),
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
                    schedule_translate[row["command"]],
                    schedule_translate[row["template_type"]],
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
        self.existing_schedule_window.update_idletasks()
        self.existing_schedule_window.attributes("-alpha", 1.0)

    class TroopsWindow:
        def __init__(
            self, parent: "Scheduler", troops: dict, troops_type: str, settings: dict
        ) -> None:

            master = ttk.Toplevel(parent, overrideredirect=True, alpha=0)

            images = parent.main_window.images

            inner_frame = ttk.Frame(
                master, borderwidth=1, relief="groove", padding=(0, 0, 10, 10)
            )
            inner_frame.grid(row=0, column=0)

            if troops_type == "off":
                ttk.Label(inner_frame, text=translate("Offensive troops")).grid(
                    row=0, column=0, columnspan=4, padx=(10, 0), pady=(6, 0)
                )
            else:
                ttk.Label(inner_frame, text=translate("Deffensive troops")).grid(
                    row=0, column=0, columnspan=4, padx=(10, 0), pady=(6, 0)
                )

            parent.include_troops = {}
            troops_template = f"only_{troops_type}_troops"
            settings["scheduler"].setdefault(troops_template, {})
            for index, troop in enumerate(TROOPS):
                if troop == "snob":
                    continue
                parent.include_troops[troop] = ttk.IntVar()
                ttk.Checkbutton(
                    inner_frame,
                    image=getattr(images, troop),
                    variable=parent.include_troops[troop],
                ).grid(
                    row=index % 4 + 1 if index < 10 else index % 10 + 1,
                    column=index // 4 if index < 10 else 3,
                    padx=(10, 0),
                    pady=(10, 0),
                )
                if settings["scheduler"][troops_template]:
                    parent.include_troops[troop].set(
                        settings["scheduler"][troops_template][troop]
                    )
                elif troop in troops:
                    parent.include_troops[troop].set(True)

            if troops_type == "off":
                center(window=master, parent=parent.settings_off_troops)
            else:
                center(window=master, parent=parent.settings_deff_troops)
            master.attributes("-alpha", 1.0)

            screen_gray = ttk.Toplevel(alpha=0.5, topmost=True)
            screen_gray.attributes("-fullscreen", True)

            ttk.Frame(screen_gray, bootstyle=ttk.SECONDARY).grid(
                row=0, column=0, sticky=ttk.NSEW
            )

            def destroy(event) -> None:
                for troop, include in parent.include_troops.items():
                    settings["scheduler"][troops_template][troop] = include.get()

                screen_gray.destroy()
                master.destroy()

            screen_gray.bind("<Button-1>", destroy)

            master.after_idle(lambda: master.attributes("-topmost", 1))
            master.after_idle(lambda: master.lift(screen_gray))
