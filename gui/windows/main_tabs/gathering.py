from functools import partial
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap import localization
from ttkbootstrap.validation import add_validation

from gui.functions import change_state, is_int
from gui.widgets.my_widgets import ScrollableFrame

if TYPE_CHECKING:
    from gui.windows.main import MainWindow

translate = localization.MessageCatalog.translate


class Gathering(ScrollableFrame):
    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ) -> None:

        super().__init__(master=parent)
        self.columnconfigure((0, 1), weight=1)

        self.invalid = 0
        add_int_validation = partial(
            add_validation,
            func=is_int,
            navi_button=main_window.navigation.gathering,
            parent=self,
        )

        self.entries_content = entries_content
        self.entries_content["gathering"] = {}
        self.entries_content["gathering_troops"] = {
            "spear": {
                "left_in_village": ttk.IntVar(),
                "send_max": ttk.IntVar(),
            },
            "sword": {
                "left_in_village": ttk.IntVar(),
                "send_max": ttk.IntVar(),
            },
            "axe": {
                "left_in_village": ttk.IntVar(),
                "send_max": ttk.IntVar(),
            },
            "archer": {
                "left_in_village": ttk.IntVar(),
                "send_max": ttk.IntVar(),
            },
            "light": {
                "left_in_village": ttk.IntVar(),
                "send_max": ttk.IntVar(),
            },
            "marcher": {
                "left_in_village": ttk.IntVar(),
                "send_max": ttk.IntVar(),
            },
            "heavy": {
                "left_in_village": ttk.IntVar(),
                "send_max": ttk.IntVar(),
            },
            "knight": {
                "left_in_village": ttk.IntVar(),
                "send_max": ttk.IntVar(),
            },
        }

        gathering_troops = self.entries_content["gathering_troops"]

        self.entries_content["gathering"]["active"] = ttk.BooleanVar()
        self.active_gathering = ttk.Checkbutton(
            self,
            text=translate("Activate scavenging"),
            variable=self.entries_content["gathering"]["active"],
            onvalue=True,
            offvalue=False,
        )
        self.active_gathering.grid(row=0, column=0, columnspan=2, padx=5, pady=(15, 20))
        self.active_gathering.configure(
            command=partial(
                change_state,
                self,
                "active",
                self.entries_content["gathering"],
                True,
                self.active_gathering,
            ),
        )

        ttk.Separator(self, orient="horizontal").grid(
            row=1, column=0, columnspan=2, sticky=("W", "E")
        )

        ttk.Label(self, text=translate("Settings")).grid(
            row=5, columnspan=2, padx=10, pady=(20, 15), sticky="W"
        )

        ttk.Label(self, text=translate("Scavenging group")).grid(
            row=6, column=0, padx=(30, 5), pady=5, sticky="W"
        )

        self.entries_content["gathering_group"] = ttk.StringVar()
        self.gathering_group = ttk.Combobox(
            self,
            textvariable=self.entries_content["gathering_group"],
            justify="center",
            width=16,
            state="readonly",
        )
        self.gathering_group.grid(row=6, column=1, padx=(5, 30), pady=5, sticky="E")
        self.gathering_group["values"] = settings["groups"]

        self.gathering_max_resources = ttk.Label(
            self, text=translate("Maximum resources to gather")
        )
        self.gathering_max_resources.grid(
            row=7, column=0, padx=(30, 5), pady=(10, 5), sticky="W"
        )

        self.entries_content["gathering_max_resources"] = ttk.IntVar()
        self.gathering_max_resources_input = ttk.Entry(
            self,
            textvariable=self.entries_content["gathering_max_resources"],
            justify="center",
            width=18,
        )
        self.gathering_max_resources_input.grid(
            row=7, column=1, padx=(5, 30), pady=(10, 5), sticky="E"
        )
        add_int_validation(self.gathering_max_resources_input, default=500)

        ttk.Label(self, text=translate("Allowed units to be used")).grid(
            row=8, columnspan=2, padx=10, pady=(20, 15), sticky="W"
        )

        troops_frame = ttk.Frame(self)
        troops_frame.grid(row=9, columnspan=2, sticky="EW")
        # troops_frame.columnconfigure(1, weight=1)
        # troops_frame.columnconfigure(2, weight=1)
        troops_frame.columnconfigure(3, weight=1)
        # troops_frame.columnconfigure(4, weight=1)
        # troops_frame.columnconfigure(5, weight=1)

        ttk.Label(troops_frame, text=translate("Leave min")).grid(
            row=8, column=1, padx=10, pady=(0, 5)
        )
        ttk.Label(troops_frame, text=translate("Send max")).grid(
            row=8, column=2, pady=(0, 5)
        )
        ttk.Label(troops_frame, text=translate("Leave min")).grid(
            row=8, column=4, padx=10, pady=(0, 5)
        )
        ttk.Label(troops_frame, text=translate("Send max")).grid(
            row=8, column=5, padx=(0, 30), pady=(0, 5)
        )

        def troop_entry_state(troop: str):
            change_state(
                [
                    self.__getattribute__(f"{troop}_left"),
                    self.__getattribute__(f"{troop}_max"),
                ],
                self.entries_content["gathering_troops"][troop]["use"].get(),
                reverse=True,
            )

        self.entries_content["gathering_troops"]["spear"]["use"] = ttk.BooleanVar()
        self.gathering_spear = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.spear,
            compound="left",
            variable=self.entries_content["gathering_troops"]["spear"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("spear"),
        )
        self.gathering_spear.grid(row=9, column=0, padx=(30, 0), pady=5, sticky="W")
        self.spear_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["spear"]["left_in_village"],
            justify=ttk.CENTER,
        )
        self.spear_left.grid(row=9, column=1, pady=5)
        self.spear_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["spear"]["send_max"],
            justify=ttk.CENTER,
        )
        self.spear_max.grid(row=9, column=2, pady=5)

        self.entries_content["gathering_troops"]["light"]["use"] = ttk.BooleanVar()
        self.gathering_light = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.light,
            compound="left",
            variable=self.entries_content["gathering_troops"]["light"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("light"),
        )
        self.gathering_light.grid(row=9, column=3, pady=5, sticky=ttk.E)
        self.light_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["light"]["left_in_village"],
            justify=ttk.CENTER,
        )
        self.light_left.grid(row=9, column=4, pady=5)
        self.light_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["light"]["send_max"],
            justify=ttk.CENTER,
        )
        self.light_max.grid(row=9, column=5, pady=5, padx=(0, 25))

        self.entries_content["gathering_troops"]["sword"]["use"] = ttk.BooleanVar()
        self.gathering_sword = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.sword,
            compound="left",
            variable=self.entries_content["gathering_troops"]["sword"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("sword"),
        )
        self.gathering_sword.grid(row=10, column=0, padx=(30, 0), pady=5, sticky="W")
        self.sword_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["sword"]["left_in_village"],
            justify=ttk.CENTER,
        )
        self.sword_left.grid(row=10, column=1, pady=5)
        self.sword_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["sword"]["send_max"],
            justify=ttk.CENTER,
        )
        self.sword_max.grid(row=10, column=2, pady=5)

        self.entries_content["gathering_troops"]["marcher"]["use"] = ttk.BooleanVar()
        self.gathering_marcher = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.marcher,
            compound="left",
            variable=self.entries_content["gathering_troops"]["marcher"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("marcher"),
        )
        self.gathering_marcher.grid(row=10, column=3, pady=5, sticky=ttk.E)
        self.marcher_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["marcher"]["left_in_village"],
            justify=ttk.CENTER,
        )
        self.marcher_left.grid(row=10, column=4, pady=5)
        self.marcher_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["marcher"]["send_max"],
            justify=ttk.CENTER,
        )
        self.marcher_max.grid(row=10, column=5, pady=5, padx=(0, 25))

        self.entries_content["gathering_troops"]["axe"]["use"] = ttk.BooleanVar()
        self.gathering_axe = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.axe,
            compound="left",
            variable=self.entries_content["gathering_troops"]["axe"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("axe"),
        )
        self.gathering_axe.grid(row=11, column=0, padx=(30, 0), pady=5, sticky="W")
        self.axe_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["axe"]["left_in_village"],
            justify=ttk.CENTER,
        )
        self.axe_left.grid(row=11, column=1, pady=5)
        self.axe_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["axe"]["send_max"],
            justify=ttk.CENTER,
        )
        self.axe_max.grid(row=11, column=2, pady=5)

        self.entries_content["gathering_troops"]["heavy"]["use"] = ttk.BooleanVar()
        self.gathering_heavy = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.heavy,
            compound="left",
            variable=self.entries_content["gathering_troops"]["heavy"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("heavy"),
        )
        self.gathering_heavy.grid(row=11, column=3, pady=5, sticky=ttk.E)
        self.heavy_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["heavy"]["left_in_village"],
            justify=ttk.CENTER,
        )
        self.heavy_left.grid(row=11, column=4, pady=5)
        self.heavy_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["heavy"]["send_max"],
            justify=ttk.CENTER,
        )
        self.heavy_max.grid(row=11, column=5, pady=5, padx=(0, 25))

        self.entries_content["gathering_troops"]["archer"]["use"] = ttk.BooleanVar()
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
            row=12, column=0, padx=(30, 0), pady=(5, 10), sticky="W"
        )
        self.archer_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["archer"]["left_in_village"],
            justify=ttk.CENTER,
        )
        self.archer_left.grid(row=12, column=1, pady=5)
        self.archer_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["archer"]["send_max"],
            justify=ttk.CENTER,
        )
        self.archer_max.grid(row=12, column=2, pady=5)

        self.entries_content["gathering_troops"]["knight"]["use"] = ttk.BooleanVar()
        self.gathering_knight = ttk.Checkbutton(
            troops_frame,
            image=main_window.images.knight,
            compound="left",
            variable=self.entries_content["gathering_troops"]["knight"]["use"],
            onvalue=True,
            offvalue=False,
            command=lambda: troop_entry_state("knight"),
        )
        self.gathering_knight.grid(row=12, column=3, pady=(5, 10), sticky=ttk.E)
        self.knight_left = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["knight"]["left_in_village"],
            justify=ttk.CENTER,
        )
        self.knight_left.grid(row=12, column=4, pady=5)
        self.knight_max = ttk.Entry(
            troops_frame,
            width=5,
            textvariable=gathering_troops["knight"]["send_max"],
            justify=ttk.CENTER,
        )
        self.knight_max.grid(row=12, column=5, pady=5, padx=(0, 25))

        # Validate troops entry
        add_int_validation(self.spear_left)
        add_int_validation(self.spear_max)
        add_int_validation(self.sword_left)
        add_int_validation(self.sword_max)
        add_int_validation(self.axe_left)
        add_int_validation(self.axe_max)
        add_int_validation(self.archer_left)
        add_int_validation(self.archer_max)
        add_int_validation(self.light_left)
        add_int_validation(self.light_max)
        add_int_validation(self.marcher_left)
        add_int_validation(self.marcher_max)
        add_int_validation(self.heavy_left)
        add_int_validation(self.heavy_max)
        add_int_validation(self.knight_left)
        add_int_validation(self.knight_max)

        ttk.Label(self, text=translate("Other settings")).grid(
            row=13, columnspan=2, padx=10, pady=(20, 15), sticky="W"
        )

        self.entries_content["gathering"]["auto_adjust"] = ttk.BooleanVar()
        self.auto_skip_level = ttk.Checkbutton(
            self,
            text=translate("Skip first level scavenging if it is profitable"),
            variable=self.entries_content["gathering"]["auto_adjust"],
            onvalue=True,
            offvalue=False,
        )
        self.auto_skip_level.grid(
            row=15, column=0, columnspan=2, padx=30, pady=10, sticky=ttk.W
        )

        self.entries_content["gathering"]["stop_if_incoming_attacks"] = ttk.BooleanVar()
        self.stop_if_incoming_attacks = ttk.Checkbutton(
            self,
            text=translate("Stop sending when incoming attacks are detected"),
            variable=self.entries_content["gathering"]["stop_if_incoming_attacks"],
            onvalue=True,
            offvalue=False,
        )
        self.stop_if_incoming_attacks.grid(
            row=16, column=0, columnspan=2, padx=30, pady=10, sticky=ttk.W
        )
