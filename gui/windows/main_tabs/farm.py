import threading
from functools import partial
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap import localization
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.validation import add_validation

from gui.functions import change_state, is_int
from gui.widgets.my_widgets import ScrollableFrame

if TYPE_CHECKING:
    from gui.windows.main import MainWindow

translate = localization.MessageCatalog.translate


class Farm(ScrollableFrame):
    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ) -> None:
        super().__init__(master=parent, max_height=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.invalid = 0
        add_int_validation = partial(
            add_validation,
            func=is_int,
            navi_button=main_window.navigation.farm,
            parent=self,
        )

        self.entries_content = entries_content

        templates = ttk.Notebook(self)
        templates.grid(row=0, column=0, pady=(0, 5), padx=5, sticky=ttk.NSEW)

        # Create notebooks for for all templates A, B, C
        for template in ("A", "B", "C"):
            self.__setattr__(f"master_{template}", ttk.Frame(templates))
            master: ttk.Frame = self.__getattribute__(f"master_{template}")
            master.columnconfigure(0, weight=1)
            master.columnconfigure(1, weight=1)
            templates.add(master, text=f"{translate('Template')} {template}")

            self.entries_content[template] = {}

            self.entries_content[template]["active"] = ttk.BooleanVar()
            self.__setattr__(
                f"active_{template}",
                ttk.Checkbutton(
                    master,
                    text=translate("Activate template"),
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
            frame.grid(row=2, columnspan=2, sticky=ttk.NSEW, padx=0, pady=20)
            frame.columnconfigure(1, weight=1)

            if "farm_group" not in self.entries_content:
                self.entries_content["farm_group"] = ttk.StringVar()
            ttk.Label(frame, text=translate("Loot group")).grid(
                row=0, column=0, padx=(10, 0), pady=(10), sticky="W"
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

            ttk.Label(master, text=translate("Wall level")).grid(
                row=4, column=0, columnspan=2, pady=(0, 15), padx=10, sticky="W"
            )

            self.entries_content[template]["wall_ignore"] = ttk.BooleanVar()
            wall_ignore = ttk.Checkbutton(
                master,
                text=translate("Ignore wall level"),
                variable=self.entries_content[template]["wall_ignore"],
                onvalue=True,
                offvalue=False,
            )
            wall_ignore.grid(row=5, column=0, pady=5, padx=(30, 5), sticky="W")

            ttk.Label(master, text="Min").grid(
                row=6, column=0, pady=5, padx=(30, 5), sticky="W"
            )

            self.entries_content[template]["min_wall"] = ttk.IntVar()
            min_wall_level_input = ttk.Entry(
                master,
                width=5,
                textvariable=self.entries_content[template]["min_wall"],
                justify="center",
            )
            min_wall_level_input.grid(row=6, column=1, pady=5, padx=(5, 25), sticky="E")
            add_int_validation(min_wall_level_input)

            ttk.Label(master, text="Max").grid(
                row=7, column=0, pady=5, padx=(30, 5), sticky="W"
            )

            self.entries_content[template]["max_wall"] = ttk.IntVar()
            max_wall_level_input = ttk.Entry(
                master,
                width=5,
                textvariable=self.entries_content[template]["max_wall"],
                justify="center",
            )
            max_wall_level_input.grid(row=7, column=1, pady=5, padx=(5, 25), sticky="E")
            add_int_validation(max_wall_level_input)

            # Wall ingore set command with partial func
            wall_ignore.configure(
                command=partial(
                    change_state,
                    [min_wall_level_input, max_wall_level_input],
                    "wall_ignore",
                    self.entries_content[template],
                ),
            )

            ttk.Label(master, text=translate("Attacks to send")).grid(
                row=8, column=0, columnspan=2, pady=(20, 15), padx=10, sticky="W"
            )

            self.entries_content[template]["max_attacks"] = ttk.BooleanVar()
            self.__setattr__(
                f"max_attacks_{template}",
                ttk.Checkbutton(
                    master,
                    text=translate("Maximum amount"),
                    variable=self.entries_content[template]["max_attacks"],
                    onvalue=True,
                    offvalue=False,
                ),
            )
            max_attacks: ttk.Checkbutton = self.__getattribute__(
                f"max_attacks_{template}"
            )
            max_attacks.grid(row=9, column=0, pady=5, padx=(30, 5), sticky="W")

            ttk.Label(master, text=translate("Attacks amount")).grid(
                row=10, column=0, pady=(5, 10), padx=(30, 5), sticky="W"
            )

            self.entries_content[template]["attacks_number"] = ttk.IntVar()
            attacks_number_input = ttk.Entry(
                master,
                width=5,
                textvariable=self.entries_content[template]["attacks_number"],
                justify="center",
            )
            attacks_number_input.grid(
                row=10, column=1, pady=(5, 10), padx=(5, 25), sticky="E"
            )
            add_int_validation(attacks_number_input, default=5, min=1)

            # Max attacks set command with partial func
            max_attacks.configure(
                command=partial(
                    change_state,
                    attacks_number_input,
                    "max_attacks",
                    self.entries_content[template],
                )
            )

            ttk.Label(master, text=translate("Other settings")).grid(
                row=11, column=0, padx=10, pady=(20, 15), sticky="W"
            )

            ttk.Label(master, text=translate("Repeat attacks every \[min]")).grid(
                row=12, column=0, padx=(30, 5), pady=(0, 25), sticky="W"
            )

            if "farm_sleep_time" not in self.entries_content:
                self.entries_content["farm_sleep_time"] = ttk.IntVar()
            farm_sleep_time = ttk.Entry(
                master,
                textvariable=self.entries_content["farm_sleep_time"],
                width=5,
                justify="center",
            )
            farm_sleep_time.grid(
                row=12, column=1, padx=(5, 25), pady=(0, 25), sticky="E"
            )
            add_int_validation(farm_sleep_time, default=30, min=1)

        farm_settings = ttk.Frame(templates)

        templates.add(farm_settings, text=translate("Additional rules"))

        self.scroll_able = ScrollableFrame(master=farm_settings, autohide=False)
        self.scroll_able.place(rely=0.0, relheight=1.0, relwidth=1.0)
        self.scroll_able.columnconfigure((0, 1), weight=1)
        farm_settings = self.scroll_able

        for template, row in zip(("A", "B", "C"), (1, 7, 13)):
            ttk.Label(farm_settings, text=f"{translate('Template')} {template}").grid(
                row=row, padx=10, pady=16, sticky=ttk.W
            )
            ttk.Label(farm_settings, text=translate("Send troops if:")).grid(
                row=row + 1, padx=25, pady=(0, 10), sticky=ttk.W
            )
            farm_rules = self.entries_content[template]["farm_rules"] = {}
            farm_rules["loot"] = ttk.StringVar(value="mix_loot")
            max_loot = ttk.Radiobutton(
                farm_settings,
                text=translate("Last attack returned with full loot:"),
                value="max_loot",
                variable=farm_rules["loot"],
            )
            max_loot.grid(row=row + 2, padx=45, pady=(5, 5), sticky=ttk.W)
            min_loot = ttk.Radiobutton(
                farm_settings,
                text=translate("Last attack returned without full loot:"),
                value="min_loot",
                variable=farm_rules["loot"],
            )
            min_loot.grid(row=row + 3, padx=45, pady=5, sticky=ttk.W)
            mix_loot = ttk.Radiobutton(
                farm_settings,
                text=translate("Send always regardless of the size of the loot:"),
                value="mix_loot",
                variable=farm_rules["loot"],
            )
            mix_loot.grid(row=row + 4, padx=45, pady=(5, 5), sticky=ttk.W)

            tooltip_frame = ttk.Frame(farm_settings)
            tooltip_frame.grid(
                row=row + 5, column=0, padx=(25, 0), pady=(10, 15), sticky=ttk.W
            )
            ttk.Label(
                tooltip_frame,
                text=translate("Maximum travel time \[min]"),
            ).grid(row=0, column=0, sticky=ttk.W)
            info = ttk.Label(tooltip_frame, image=main_window.images.question)
            info.grid(row=0, column=1, padx=(5, 0))
            farm_rules["max_travel_time"] = ttk.IntVar()
            ToolTip(
                info,
                text=translate(
                    "Defines the maximum duration of a one-way march.\n\n"
                    "Starting village -> barbarian village.\n\n"
                    "Default value 0 means no time limit."
                ),
                wraplength=350,
                topmost=True,
            )
            max_travel_time = ttk.Entry(
                farm_settings,
                textvariable=farm_rules["max_travel_time"],
                width=5,
                justify=ttk.CENTER,
            )
            max_travel_time.grid(
                row=row + 5, column=1, padx=(0, 25), pady=(10, 15), sticky=ttk.E
            )
            add_int_validation(max_travel_time)

    def height_fix(self) -> None:
        if (self.master.winfo_height() - self.winfo_reqheight()) > 0:
            self.master_A.rowconfigure(
                666,
                minsize=(self.master.winfo_height() - self.winfo_reqheight()),
            )
