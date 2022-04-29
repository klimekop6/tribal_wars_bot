import ctypes
import json
import logging
import os
import subprocess
import sys
import time
import tkinter as tk

import ttkbootstrap as ttk
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(filename="log.txt", level=logging.WARNING)


def center(window: tk.Toplevel, parent: tk.Toplevel = None) -> None:
    """Place window in the center of a screen or parent widget"""

    window.update_idletasks()
    if parent:
        window_geometry = window.winfo_geometry()
        parent_geometry = parent.winfo_geometry()
        window_x, window_y = window_geometry[: window_geometry.find("+")].split("x")
        parent_x, parent_y = parent_geometry[: parent_geometry.find("+")].split("x")
        window.geometry(
            f"+{int(int(parent.winfo_rootx()) + int(parent_x)/2 - int(window_x)/2)}"
            f"+{int(int(parent.winfo_rooty()) + int(parent_y)/2 - int(window_y)/2)}"
        )
    else:
        window.geometry(
            f"+{int(window.winfo_screenwidth()/2 - window.winfo_reqwidth()/2)}"
            f"+{int(window.winfo_screenheight()/2 - window.winfo_reqheight()/2)}"
        )


def change_state(parent, value, entries_content, reverse=False, *ommit) -> None:
    def disableChildren(parent):
        if not parent.winfo_children():
            if parent.winfo_class() not in ("TFrame", "Labelframe", "TSeparator"):
                parent.config(state="disabled")
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            if wtype not in ("TFrame", "Labelframe", "TSeparator"):
                if child not in ommit:
                    child.configure(state="disable")
            else:
                disableChildren(child)

    def enableChildren(parent):
        if not parent.winfo_children():
            if parent.winfo_class() not in ("TFrame", "Labelframe", "TSeparator"):
                parent.config(state="normal")
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            if wtype not in ("TFrame", "Labelframe", "TSeparator"):
                if child not in ommit:
                    if wtype == "TCombobox":
                        child.configure(state="readonly")
                    else:
                        child.configure(state="normal")
            else:
                enableChildren(child)

    def check_button_fix(parent):
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            if wtype not in ("TFrame"):
                if wtype in ("TCheckbutton"):
                    if child not in ommit:
                        child.invoke()
                        child.invoke()
            else:
                check_button_fix(child)

    if not isinstance(value, int):
        value = int(entries_content[value].get())

    if not isinstance(parent, list):
        parent = [parent]

    for parent_ in parent:
        if not reverse:
            if value:
                disableChildren(parent_)
            else:
                enableChildren(parent_)
                check_button_fix(parent_)
        else:
            if value:
                enableChildren(parent_)
                check_button_fix(parent_)
            else:
                disableChildren(parent_)


def change_state_on_settings_load(
    parent, name, entries_content: dict, reverse=False, *ommit
) -> None:
    if name in entries_content:
        if not entries_content[name].get():
            return
        if int(entries_content[name].get()) or reverse:
            change_state(
                parent,
                int(entries_content[name].get()),
                entries_content,
                reverse,
                *ommit,
            )


def chrome_profile_path(settings: dict) -> None:
    """Wyszukuję i zapisuje w ustawieniach aplikacji aktualną ścierzkę do profilu użytkownika przeglądarki chrome"""

    path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\TribalWars")
    settings["path"] = path
    settings["first_lunch"] = False
    settings["first_logon"] = True
    settings["last_opened_daily_bonus"] = time.strftime("%d.%m.%Y", time.localtime())

    with open("settings.json", "w") as settings_json_file:
        json.dump(settings, settings_json_file)


def current_time() -> str:
    return time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())


def custom_error(message: str, auto_hide: bool = False, parent=None) -> None:

    master = tk.Toplevel(borderwidth=1, relief="groove")
    master.attributes("-alpha", 0.0)
    master.overrideredirect(True)
    master.attributes("-topmost", 1)
    master.bell()

    message = message.splitlines()

    if not auto_hide:
        if len(message) == 1:
            message_label = ttk.Label(master, text=message[0])
            message_label.grid(row=0, column=0, padx=5, pady=5)

            ok_button = ttk.Button(master, text="ok", command=master.destroy)
            ok_button.grid(row=1, column=0, pady=(5, 8))
        else:
            for index, text_line in enumerate(message):
                if index == 0:
                    message_label = ttk.Label(master, text=text_line)
                    message_label.grid(row=index, column=0, padx=10, pady=(10, 5))
                else:
                    message_label = ttk.Label(master, text=text_line)
                    message_label.grid(row=index, column=0, padx=10, pady=(0, 5))
            ok_button = ttk.Button(master, text="ok", command=master.destroy)
            ok_button.grid(row=len(message), column=0, pady=(5, 10))

        # message_label.bind("<Button-1>", lambda event: get_pos(event, "message_label"))
        master.focus_force()
        master.bind("<Return>", lambda event: master.destroy())
        center(master, parent=parent)
        master.attributes("-alpha", 1.0)
        master.grab_set()
        ok_button.wait_window(master)

    if auto_hide:
        message_label = ttk.Label(master, text=message[0])
        message_label.grid(row=1, column=0, padx=10, pady=8)
        center(master, parent=parent)
        master.attributes("-alpha", 1.0)
        master.after(ms=2000, func=lambda: master.destroy())


def fill_entry_from_settings(entries: dict, settings: dict) -> None:
    def loop_over_entries(entries: dict | tk.StringVar, settings: dict | str):
        for key in entries:
            if key in settings:
                if settings[key]:
                    if isinstance(entries[key], dict):
                        loop_over_entries(entries[key], settings[key])
                    else:
                        entries[key].set(settings[key])
                else:
                    if not entries[key].get():
                        entries[key].set(0)

    loop_over_entries(entries=entries, settings=settings)


def first_app_lunch(settings: dict) -> None:
    """Do some stuff if app was just installed for the 1st time"""

    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    if is_admin():
        # Code of your program here
        subprocess.run("regedit /s anticaptcha-plugin.reg")
        chrome_profile_path(settings)
    else:
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, __file__, None, 1
        )
        sys.exit()


def forget_row(widget_name, row_number: int = 0, rows_beetwen: tuple = None) -> None:
    for label in widget_name.grid_slaves():
        if rows_beetwen:
            if rows_beetwen[0] < int(label.grid_info()["row"]) < rows_beetwen[1]:
                label.grid_forget()
        elif int(label.grid_info()["row"]) == row_number:
            label.grid_forget()


def get_pos(self, event, *args) -> None:
    xwin = self.master.winfo_x()
    ywin = self.master.winfo_y()
    startx = event.x_root
    starty = event.y_root

    ywin = ywin - starty
    xwin = xwin - startx

    def move_window(event):
        self.master.geometry(f"+{event.x_root + xwin}+{event.y_root + ywin}")

    startx = event.x_root
    starty = event.y_root

    for arg in args:
        getattr(self, arg).bind("<B1-Motion>", move_window)


def paid(date: str) -> bool:
    """Return True if paid or False if not"""

    if time.strptime(current_time(), "%d/%m/%Y %H:%M:%S") > time.strptime(
        date + " 23:59:59", "%Y-%m-%d %H:%M:%S"
    ):
        return False
    return True


def invoke_checkbuttons(parent) -> None:
    def call_widget(parent) -> None:
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            if wtype == "TCheckbutton":
                child.invoke()
                child.invoke()
            else:
                call_widget(parent=child)

    call_widget(parent=parent)


def load_settings(file_path: str = "settings.json") -> dict:
    try:
        f = open(file_path)
        settings = json.load(f)
    except FileNotFoundError:
        f = open("settings.json", "w")
        settings = {"first_lunch": True}
        settings["gathering_troops"] = {
            "spear": {"use": False, "left_in_village": 0, "send_max": 0},
            "sword": {"use": False, "left_in_village": 0, "send_max": 0},
            "axe": {"use": False, "left_in_village": 0, "send_max": 0},
            "archer": {"use": False, "left_in_village": 0, "send_max": 0},
            "light": {"use": False, "left_in_village": 0, "send_max": 0},
            "marcher": {"use": False, "left_in_village": 0, "send_max": 0},
            "heavy": {"use": False, "left_in_village": 0, "send_max": 0},
            "knight": {"use": False, "left_in_village": 0, "send_max": 0},
        }
        settings["groups"] = None
        json.dump(settings, f)
    finally:
        f.close()
        return settings


def run_driver(settings: dict) -> webdriver.Chrome:
    """Uruchamia sterownik i przeglądarkę google chrome"""

    try:
        chrome_options = Options()
        chrome_options.add_argument("user-data-dir=" + settings["path"])
        chrome_options.add_argument("start-maximized")
        chrome_options.add_extension(extension="0.62.crx")
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-automation", "disable-popup-blocking"]
        )
        while True:
            try:
                driver = webdriver.Chrome(
                    service=Service(
                        ChromeDriverManager(
                            cache_valid_range=31, log_level=logging.WARNING
                        ).install()
                    ),
                    options=chrome_options,
                )
                break
            except:
                time.sleep(10)
        return driver
    except BaseException as exc:
        logging.error(exc)


def save_entry_to_settings(
    entries: dict, settings: dict, settings_by_worlds: dict = None
) -> None:
    def loop_over_entries(entries: dict | tk.StringVar, settings: dict | str):
        for key, value in entries.items():
            if isinstance(value, dict):
                if key not in settings:
                    settings[key] = {}
                loop_over_entries(entries=entries[key], settings=settings[key])
            else:
                settings[key] = value.get()

    print(settings["server_world"])
    loop_over_entries(entries=entries, settings=settings)
    print(settings["server_world"])
    if settings_by_worlds:
        loop_over_entries(
            entries=entries, settings=settings_by_worlds[settings["server_world"]]
        )

    # if "temp" in settings:
    #     del settings["temp"]

    # with open("settings.json", "w") as settings_json_file:
    #     json.dump(settings, settings_json_file)

    # if not settings["world_number"] or settings["world_number"] == "0":
    #     return

    # if not os.path.isdir("settings"):
    #     os.mkdir("settings")

    # with open(f'settings/{settings["server_world"]}.json', "w") as settings_json_file:
    #     json.dump(settings, settings_json_file)
