from functools import partial
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap import localization
from ttkbootstrap.validation import add_validation

from app_functions import get_villages_id
from gui_functions import change_state, custom_error, is_int
from my_widgets import ScrollableFrame

if TYPE_CHECKING:
    from app_gui.windows.main_window import MainWindow

translate = localization.MessageCatalog.translate


class Coins(ScrollableFrame):
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
            navi_button=main_window.navigation.coins,
            parent=self,
        )

        self.main_window = main_window
        self.settings = settings
        settings.setdefault("coins", {"villages": {}})
        settings["coins"].setdefault("villages", {})
        entries_content.setdefault("coins", {})

        entries_content["coins"]["mine_coin"] = ttk.BooleanVar()
        self.check_mine_coin = ttk.Checkbutton(
            self,
            text=translate("Activate coin minting"),
            variable=entries_content["coins"]["mine_coin"],
            onvalue=True,
            offvalue=False,
        )
        self.check_mine_coin.grid(row=0, column=0, columnspan=2, padx=5, pady=(15, 20))
        self.check_mine_coin.configure(
            command=partial(
                change_state,
                self,
                "mine_coin",
                entries_content["coins"],
                True,
                self.check_mine_coin,
            ),
        )

        ttk.Separator(self, orient="horizontal").grid(
            row=1, column=0, columnspan=2, sticky=("W", "E")
        )

        self.villages_frame = ttk.Labelframe(
            self, text=translate("Villages"), height=110, width=340, labelanchor=ttk.N
        )
        self.villages_frame.grid(row=2, column=0, columnspan=2, pady=(20, 5))
        self.villages_frame.grid_propagate(0)
        self.scrollable_frame = ScrollableFrame(self.villages_frame, height=50)
        self.scrollable_frame.place(rely=0.0, relheight=1.0, relwidth=1.0)
        self.scrollable_frame.columnconfigure((0, 1, 2), weight=1, uniform="column")

        frame = ttk.Frame(self)
        frame.grid(row=3, column=0, columnspan=2, pady=(20, 5))

        self.villages = ttk.Entry(
            frame,
            justify=ttk.CENTER,
            width=8,
        )
        self.villages.grid(row=3, column=0, padx=5)

        def add_village() -> None:

            village = self.villages.get().strip()
            villages = get_villages_id(settings=settings)
            if village in villages:
                village_id = villages[village][:-1]
            else:
                villages = get_villages_id(settings=settings, update=True)
                if village not in villages:
                    custom_error(
                        message=f"""{translate("Village")} {village} {translate("doesn't exist.")}""",
                        parent=self.master,
                    )
                    return
                village_id = villages[village][:-1]
            if village in settings["coins"]["villages"]:
                custom_error(translate("Village is already in use"), parent=self.master)
                return
            settings["coins"]["villages"][village] = village_id
            self.villages.delete(0, "end")
            self.VillageButton(self, self.scrollable_frame, village)

        def clear_hint(widget: ttk.Entry) -> None:
            if widget.get() == "XXX|YYY" and str(widget["state"]) != "disable":
                widget.config(foreground="white")
                widget.delete(0, "end")
                widget.unbind("<Button-1>")

        def text_hint(widget: ttk.Entry) -> None:
            widget.config(foreground="#555555")
            widget.insert(0, "XXX|YYY")

        text_hint(self.villages)
        self.villages.bind("<Button-1>", lambda _: clear_hint(self.villages))

        self.add_village_to_mine_coin = ttk.Button(
            frame,
            text=translate("Add"),
            command=add_village,
        )
        self.add_village_to_mine_coin.grid(row=3, column=1, padx=5)

        ttk.Label(self, text=translate("Fill granaries up to \[%]")).grid(
            row=4,
            column=0,
            columnspan=2,
            padx=(30, 0),
            pady=(40, 0),
            sticky=ttk.W,
        )
        entries_content["coins"]["resource_fill"] = ttk.IntVar()
        self.resource_fill = ttk.Entry(
            self,
            width=6,
            textvariable=entries_content["coins"]["resource_fill"],
            justify=ttk.CENTER,
        )
        self.resource_fill.grid(
            row=4, column=1, padx=(5, 30), pady=(40, 0), sticky=ttk.E
        )
        add_int_validation(self.resource_fill)

        ttk.Label(self, text=translate("Reserved resources in villages")).grid(
            row=5,
            column=0,
            columnspan=2,
            padx=(30, 0),
            pady=(20, 0),
            sticky=ttk.W,
        )
        entries_content["coins"]["resource_left"] = ttk.IntVar()
        self.resource_left = ttk.Entry(
            self,
            width=6,
            textvariable=entries_content["coins"]["resource_left"],
            justify=ttk.CENTER,
        )
        self.resource_left.grid(
            row=5, column=1, padx=(5, 30), pady=(20, 0), sticky=ttk.E
        )
        add_int_validation(self.resource_left)

        ttk.Label(
            self,
            text=translate(
                "Maximum time for transporting resources to the village \[min]"
            ),
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            padx=(30, 0),
            pady=(20, 0),
            sticky=ttk.W,
        )
        entries_content["coins"]["max_send_time"] = ttk.IntVar(value=120)
        self.max_send_time = ttk.Entry(
            self,
            width=6,
            textvariable=entries_content["coins"]["max_send_time"],
            justify=ttk.CENTER,
        )
        self.max_send_time.grid(
            row=6, column=1, padx=(5, 30), pady=(20, 0), sticky=ttk.E
        )
        add_int_validation(self.max_send_time, default=120, min=1)

        ttk.Label(
            self, text=translate("Mint coins and call resources every \[min]")
        ).grid(
            row=7,
            column=0,
            columnspan=2,
            padx=(30, 0),
            pady=(20, 0),
            sticky=ttk.W,
        )
        entries_content["coins"]["check_every"] = ttk.IntVar()
        self.check_every = ttk.Entry(
            self,
            width=6,
            textvariable=entries_content["coins"]["check_every"],
            justify=ttk.CENTER,
        )
        self.check_every.grid(row=7, column=1, padx=(5, 30), pady=(20, 0), sticky=ttk.E)
        add_int_validation(self.check_every, default=30, min=1)

        self.draw_choosed_villges()

    def draw_choosed_villges(self) -> None:
        for index, village in enumerate(self.settings["coins"]["villages"]):
            row = index // 3
            column = index % 3
            self.VillageButton(
                self,
                self.scrollable_frame,
                village,
                row=row,
                column=column,
            )

    def redraw_choosed_villges(self) -> None:
        for widget in self.scrollable_frame.content_grid_slaves():
            widget.destroy()
        self.draw_choosed_villges()

    class VillageButton:
        def __init__(
            self, parent: "Coins", master: ttk.Labelframe, village: str, **kwargs
        ) -> None:
            self.parent = parent
            self.master = master
            self.village = village
            self.frame = ttk.Frame(master, borderwidth=1, relief="solid")
            if kwargs:
                self.frame.grid(padx=10, pady=(10, 0), **kwargs)
            else:
                self.frame.grid(padx=10, pady=(10, 0), **self.calc_grid_settings())
            self.coords = ttk.Label(
                self.frame, text=village, anchor=ttk.CENTER, border=0
            )
            self.coords.grid(row=0, column=0, padx=(8, 7), pady=(3, 4))
            ttk.Separator(
                self.frame, orient=ttk.VERTICAL, style="default.TSeparator"
            ).grid(row=0, column=1, sticky=ttk.NS)
            self.exit = ttk.Label(
                self.frame, image=parent.main_window.images.exit, border=0
            )
            self.exit.grid(row=0, column=2, padx=(4, 5))

            def enter(event) -> None:
                self.exit.config(image=parent.main_window.images.exit_hover)
                self.exit.grid(row=0, column=2, padx=(1, 2))

            def leave(event) -> None:
                self.exit.config(image=parent.main_window.images.exit)
                self.exit.grid(row=0, column=2, padx=(4, 5))

            self.exit.bind("<Button-1>", lambda _: self.delete())
            self.exit.bind("<Enter>", enter)
            self.exit.bind("<Leave>", leave)

        def calc_grid_settings(self) -> dict:
            villages = len(self.parent.settings["coins"]["villages"]) - 1
            row = villages // 3
            column = villages % 3
            return {"row": row, "column": column}

        def delete(self) -> None:
            del self.parent.settings["coins"]["villages"][self.village]
            self.frame.destroy()
