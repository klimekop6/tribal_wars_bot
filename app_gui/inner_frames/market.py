from functools import partial
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap import localization
from ttkbootstrap.validation import add_validation

from gui_functions import change_state, is_int
from my_widgets import ScrollableFrame

if TYPE_CHECKING:
    from app_gui.windows.main_window import MainWindow

translate = localization.MessageCatalog.translate


class Market(ScrollableFrame):
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
            navi_button=main_window.navigation.market,
            parent=self,
        )

        entries_content["market"] = {"wood": {}, "stone": {}, "iron": {}}
        market = entries_content["market"]

        market["premium_exchange"] = ttk.BooleanVar()
        self.active_premium_exchange = ttk.Checkbutton(
            self,
            text=translate("Activate market premium"),
            variable=market["premium_exchange"],
            onvalue=True,
            offvalue=False,
        )
        self.active_premium_exchange.configure(
            command=partial(
                change_state,
                self,
                "premium_exchange",
                market,
                True,
                self.active_premium_exchange,
            ),
        )
        self.active_premium_exchange.grid(
            row=0, column=0, columnspan=2, padx=5, pady=(15, 20)
        )

        ttk.Separator(self, orient="horizontal").grid(
            row=1, column=0, columnspan=2, sticky=("W", "E")
        )

        # Maksymalny kurs sprzedaży
        ttk.Label(self, text=translate("Maximum selling rate")).grid(
            row=3, column=0, padx=10, pady=(20, 10), sticky="W"
        )

        self.wood_photo = ttk.PhotoImage(file="icons//wood.png")
        ttk.Label(
            self,
            text=translate("Wood"),
            image=self.wood_photo,
            compound="left",
        ).grid(row=4, column=0, padx=(30, 5), pady=(10, 5), sticky="W")
        market["wood"]["max_exchange_rate"] = ttk.IntVar()
        self.max_wood_exchange_rate = ttk.Entry(
            self,
            textvariable=market["wood"]["max_exchange_rate"],
            justify="center",
            width=6,
        )
        self.max_wood_exchange_rate.grid(
            row=4, column=1, padx=(5, 30), pady=(10, 5), sticky="E"
        )
        add_int_validation(self.max_wood_exchange_rate)

        self.stone_photo = ttk.PhotoImage(file="icons//stone.png")
        ttk.Label(
            self,
            text=translate("Stone"),
            image=self.stone_photo,
            compound="left",
        ).grid(row=5, column=0, padx=(30, 5), pady=(10, 5), sticky="W")
        market["stone"]["max_exchange_rate"] = ttk.IntVar()
        self.max_stone_exchange_rate = ttk.Entry(
            self,
            textvariable=market["stone"]["max_exchange_rate"],
            justify="center",
            width=6,
        )
        self.max_stone_exchange_rate.grid(
            row=5, column=1, padx=(5, 30), pady=(10, 5), sticky="E"
        )
        add_int_validation(self.max_stone_exchange_rate)

        self.iron_photo = ttk.PhotoImage(file="icons//iron.png")
        ttk.Label(
            self,
            text=translate("Iron"),
            image=self.iron_photo,
            compound="left",
        ).grid(row=6, column=0, padx=(30, 5), pady=(10, 5), sticky="W")
        market["iron"]["max_exchange_rate"] = ttk.IntVar()
        self.max_iron_exchange_rate = ttk.Entry(
            self,
            textvariable=market["iron"]["max_exchange_rate"],
            justify="center",
            width=6,
        )
        self.max_iron_exchange_rate.grid(
            row=6, column=1, padx=(5, 30), pady=(10, 5), sticky="E"
        )
        add_int_validation(self.max_iron_exchange_rate)

        # Zapas surowców w wioskach
        ttk.Label(self, text=translate("Reserved resources in villages")).grid(
            row=9, column=0, padx=10, pady=(15, 10), sticky="W"
        )

        ttk.Label(
            self,
            text=translate("Wood"),
            image=self.wood_photo,
            compound="left",
        ).grid(row=10, column=0, padx=(30, 5), pady=(10, 5), sticky="W")
        market["wood"]["leave_in_storage"] = ttk.IntVar()
        self.min_wood_left_in_storage = ttk.Entry(
            self,
            textvariable=market["wood"]["leave_in_storage"],
            justify="center",
            width=6,
        )
        self.min_wood_left_in_storage.grid(
            row=10, column=1, padx=(5, 30), pady=(10, 5), sticky="E"
        )
        add_int_validation(self.min_wood_left_in_storage)

        ttk.Label(
            self,
            text=translate("Stone"),
            image=self.stone_photo,
            compound="left",
        ).grid(row=11, column=0, padx=(30, 5), pady=(10, 5), sticky="W")
        market["stone"]["leave_in_storage"] = ttk.IntVar()
        self.min_stone_left_in_storage = ttk.Entry(
            self,
            textvariable=market["stone"]["leave_in_storage"],
            justify="center",
            width=6,
        )
        self.min_stone_left_in_storage.grid(
            row=11, column=1, padx=(5, 30), pady=(10, 5), sticky="E"
        )
        add_int_validation(self.min_stone_left_in_storage)

        ttk.Label(
            self,
            text=translate("Iron"),
            image=self.iron_photo,
            compound="left",
        ).grid(row=12, column=0, padx=(30, 5), pady=(10, 5), sticky="W")
        market["iron"]["leave_in_storage"] = ttk.IntVar()
        self.min_iron_left_in_storage = ttk.Entry(
            self,
            textvariable=market["iron"]["leave_in_storage"],
            justify="center",
            width=6,
        )
        self.min_iron_left_in_storage.grid(
            row=12, column=1, padx=(5, 30), pady=(10, 5), sticky="E"
        )
        add_int_validation(self.min_iron_left_in_storage)

        # Pozostałe ustawienia
        ttk.Label(self, text=translate("Other settings")).grid(
            row=13, column=0, padx=10, pady=(15, 10), sticky="W"
        )

        ttk.Label(self, text=translate("Check market rates every \[min]")).grid(
            row=14, column=0, padx=(30, 5), pady=(10, 5), sticky="W"
        )
        market["check_every"] = ttk.IntVar()
        check_every = ttk.Entry(
            self,
            textvariable=market["check_every"],
            justify="center",
            width=6,
        )
        check_every.grid(row=14, column=1, padx=(5, 30), pady=(10, 5), sticky="E")
        add_int_validation(check_every, default=30, min=1)

        def show_label_and_text_widget() -> None:
            def clear_text_widget(event) -> None:
                if self.villages_to_ommit_text.get("1.0", "1.5") == translate("Paste"):
                    self.villages_to_ommit_text.delete("1.0", "end")
                    self.villages_to_ommit_text.unbind("<Button-1>")

            def add_villages_list() -> None:
                if self.villages_to_ommit_text.compare("end-1c", "==", "1.0"):
                    self.villages_to_ommit_text.insert(
                        "1.0",
                        translate(
                            "Paste the villages in XXX | YYY format that you want to be skipped. "
                            "Villages should be separated by a space, tab, or enter. "
                            "You can also enter the entire contingent, e.g. k45 or K45"
                        ),
                    )
                    self.villages_to_ommit_text.bind("<Button-1>", clear_text_widget)
                    return
                if self.villages_to_ommit_text.get("1.0", "1.5") == translate("Paste"):
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

                self.success_label = ttk.Label(self, text="Dodano!")
                self.success_label.grid(
                    row=21, column=0, columnspan=2, padx=5, pady=(10, 15)
                )
                self.update()
                self.after(
                    1500,
                    lambda: [
                        self.success_label.grid_forget(),
                        self.update_idletasks(),
                    ],
                )
                del self.villages_to_ommit_text

            if hasattr(self, "villages_to_ommit_text"):
                self.villages_to_ommit_text.grid_forget()
                self.confirm_button.grid_forget()
                del self.villages_to_ommit_text
                return

            self.villages_to_ommit_text = ttk.Text(
                self, height=6, width=50, wrap="word"
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
                    translate(
                        "Paste the villages in XXX | YYY format that you want to be skipped. "
                        "Villages should be separated by a space, tab, or enter. "
                        "You can also enter the entire contingent, e.g. k45 or K45"
                    ),
                )

            self.confirm_button = ttk.Button(
                self, text=translate("Add"), command=add_villages_list
            )
            self.confirm_button.grid(
                row=22, column=0, columnspan=2, padx=5, pady=(5, 15)
            )
            self.villages_to_ommit_text.bind("<Button-1>", clear_text_widget)

        market["market_exclude_villages"] = ttk.StringVar()
        self.add_village_exceptions_button = ttk.Button(
            self,
            text=translate("Excluded villages list"),
            command=show_label_and_text_widget,
        )
        self.add_village_exceptions_button.grid(
            row=20, column=0, columnspan=2, padx=5, pady=(25, 5)
        )
