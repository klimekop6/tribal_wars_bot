import time
from typing import TYPE_CHECKING

from ttkbootstrap import localization
from ttkbootstrap.tableview import Tableview

if TYPE_CHECKING:
    from app_gui.windows.main_window import MainWindow

from gui_functions import center
from my_widgets import TopLevel

translate = localization.MessageCatalog.translate


class JobsToDoWindow:
    def __init__(self, main_window: "MainWindow") -> None:
        self.master = TopLevel(
            title_text=translate("Task list"), timer=main_window.time
        )

        self.translate = {
            "gathering": translate("scavenging"),
            "auto_farm": translate("looting"),
            "check_incoming_attacks": translate("attack labels"),
            "premium_exchange": translate("premium exchange"),
            "send_troops": translate("scheduler"),
            "mine_coin": translate("coin minting"),
            "daily_bonus": translate("daily bonus"),
        }

        self.content_frame = self.master.content_frame

        self.coldata = [
            {"text": translate("World"), "stretch": False},
            translate("Task"),
            {"text": translate("Execution date"), "stretch": False},
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

    def update_table(self, main_window: "MainWindow") -> None:
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
