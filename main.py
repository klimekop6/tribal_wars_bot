import locale
import logging
import os

if not os.path.exists("logs"):
    os.mkdir("logs")
import sys
import threading
import tkinter as tk
from pathlib import Path

import ttkbootstrap as ttk
from pyupdater.client import Client
from ttkbootstrap import localization
from ttkbootstrap.toast import ToastNotification

import app.functions as functions
from app.client_config import ClientConfig
from app.config import APP_NAME, APP_VERSION
from app.decorators import log_errors
from app.logging import CustomLogFormatter, get_logger
from gui.functions import center, custom_error
from gui.style import configure_style
from gui.widgets.my_widgets import TopLevel
from gui.windows.log_in import LogInWindow
from gui.windows.main import MainWindow

translate = localization.MessageCatalog.translate
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


class Updates:
    def __init__(self, root: tk.Toplevel, settings: dict) -> None:
        self.client = Client(ClientConfig())
        self.update = False
        self.root = root
        self.settings = settings

    def check(self) -> None:
        self.client.refresh()
        # Check for updates on stable channel
        if self.settings["globals"]["stable_release"]:
            app_update = self.client.update_check(APP_NAME, APP_VERSION)
        # Check for updates on any channel
        else:
            app_update = self.client.update_check(APP_NAME, APP_VERSION, strict=False)

        if app_update is not None:
            self.update = True

    def periodically_check_for_updates(self) -> None:
        if self.update:
            return
        thread = threading.Thread(target=lambda: self.check(), daemon=True)
        thread.start()
        self.thread_monitor(thread)
        self.root.after(
            ms=7_200_000,
            func=self.periodically_check_for_updates,
        )

    def start(self) -> None:
        self.root.after(
            ms=7_200_000,
            func=self.periodically_check_for_updates,
        )

    def thread_monitor(self, thread: threading.Thread) -> None:
        if thread.is_alive():
            self.root.after(500, lambda: self.thread_monitor(thread))
            return
        if self.update:
            ToastNotification(
                title="TribalWarsBot Update",
                message=f"Dostępna jest nowa wersja aplikacji. ",
                topmost=True,
                bootstyle="primary",
            ).show_toast()


@log_errors()
def check_for_updates(stable_release: bool = True) -> None:

    client = Client(ClientConfig())
    client.refresh()

    # Check for updates on stable channel
    if stable_release:
        app_update = client.update_check(APP_NAME, APP_VERSION)
    # Check for updates on any channel
    else:
        app_update = client.update_check(APP_NAME, APP_VERSION, strict=False)

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


def main() -> None:
    settings = functions.load_settings()
    settings["temp"] = {}

    # Check for updates
    if hasattr(sys, "frozen"):
        settings.setdefault("globals", {})
        if "stable_release" not in settings["globals"]:
            settings["globals"]["stable_release"] = True
        if settings["globals"]["stable_release"]:
            check_for_updates(stable_release=True)
        else:
            check_for_updates(stable_release=False)

    if settings["first_lunch"]:
        functions.first_app_lunch(settings=settings)

    hidden_root = tk.Tk()
    hidden_root.attributes("-alpha", 0)
    hidden_root.title("TribalWarsBot")

    style = ttk.Style(theme="darkly")

    configure_style(style=style)

    localization.initialize_localities()
    try:
        localization.MessageCatalog.locale(settings["globals"]["lang"])
    except KeyError:
        lang = locale.getdefaultlocale()[0]
        if "pl" in lang:
            localization.MessageCatalog.locale(lang)
            settings["globals"]["lang"] = "pl"
        else:
            lang = "en"
            localization.MessageCatalog.locale(lang)
            settings["globals"]["lang"] = "en"

    root = tk.Toplevel(hidden_root)
    main_window = MainWindow(master=root, hidden_root=hidden_root, settings=settings)
    LogInWindow(main_window=main_window, settings=settings)

    Updates(root=root, settings=settings).start()

    hidden_root.mainloop()


if __name__ == "__main__":
    # import cProfile
    # import pstats

    # with cProfile.Profile() as pr:

    main()

    # stats = pstats.Stats(pr)
    # stats.sort_stats(pstats.SortKey.TIME)
    # stats.dump_stats(filename="needs_profiling.prof")
