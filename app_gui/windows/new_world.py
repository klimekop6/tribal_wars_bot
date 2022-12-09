import os
import re
import tkinter as tk
from copy import deepcopy
from typing import TYPE_CHECKING

import requests
import xmltodict

if TYPE_CHECKING:
    from app_gui.windows.main_window import MainWindow

from typing import TYPE_CHECKING

import ttkbootstrap as ttk

from config import PYTHON_ANYWHERE_WORLD_SETTINGS
from gui_functions import (
    center,
    custom_error,
    invoke_checkbuttons,
    save_entry_to_settings,
    set_default_entries,
)
from my_widgets import TopLevel
from tribal_wars_bot_api import TribalWarsBotApi

if TYPE_CHECKING:
    from app_gui.windows.main_window import MainWindow


class NewWorldWindow:
    def __init__(
        self, parent: "MainWindow", settings: dict, obligatory: bool = False
    ) -> None:

        master = TopLevel(title_text="Tribal Wars Bot", main_window=parent.master)

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
            "tribalwars.net",
            "tribalwars.nl",
            "tribalwars.se",
            "tribalwars.com.br",
            "tribalwars.com.pt",
            "divokekmeny.cz",
            "staemme.ch",
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
            if "pl" in game_url_var.get() and re.search(
                r"^p{1}\d+", world_number.get().strip()
            ):
                pass
            elif ".net" in game_url.get() and re.search(
                r"^c{1}\d+", world_number.get().strip()
            ):
                pass
            elif not world_number.get().isnumeric():
                custom_error(
                    "Numer świata powinien składać się z samych cyfr.",
                    parent=master,
                )
                return
            if add_new_world(
                parent=parent,
                settings=settings,
                game_url=game_url_var.get(),
                world_number=world_number.get(),
            ):
                master.destroy()

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
        center(window=master, parent=parent.master)
        master.attributes("-alpha", 1.0)
        if obligatory:
            master.wait_window()


def add_new_world(
    parent: "MainWindow",
    settings: dict,
    game_url: str,
    world_number: str,
    entry_change: bool = False,
) -> bool:
    def get_world_config() -> bool:
        def on_error() -> None:
            if entry_change:
                parent.control_panel.show()
                if "world_number" in settings:
                    parent.entries_content["world_number"].set(settings["world_number"])
                if "game_url" in settings:
                    parent.entries_content["game_url"].set(settings["game_url"])
            custom_error(
                message="Błąd, upewnij się że taki świat nadal istnieje.",
                parent=parent.master,
            )

        update_settings_on_python_anywhere = False
        response = requests.get(f"{PYTHON_ANYWHERE_WORLD_SETTINGS}/{server_world}.xml")
        if not response.ok:
            response = requests.get(
                f"https://{server_world}.{game_url}/interface.php?func=get_config"
            )
            update_settings_on_python_anywhere = True

        try:
            world_config = xmltodict.parse(response.content)
        except:
            on_error()
            return False
        else:
            if update_settings_on_python_anywhere:
                TribalWarsBotApi(f"/world/{server_world}").post(
                    data=response.text, sync=False
                )

        settings["world_config"] = {
            "archer": world_config["config"]["game"]["archer"],
            "church": world_config["config"]["game"]["church"],
            "knight": world_config["config"]["game"]["knight"],
            "watchtower": world_config["config"]["game"]["watchtower"],
            "fake_limit": world_config["config"]["game"]["fake_limit"],
            "scavenging": world_config["config"]["game"]["scavenging"],
            "start_hour": world_config["config"]["night"]["start_hour"],
            "end_hour": world_config["config"]["night"]["end_hour"],
            "speed": world_config["config"]["speed"],
            "unit_speed": world_config["config"]["unit_speed"],
            "daily_bonus": None,
        }
        return True

    def set_additional_settings(
        game_url: str, country_code: str, server_world: str
    ) -> None:
        settings["game_url"] = game_url
        settings["country_code"] = country_code
        settings["server_world"] = server_world
        settings["globals"][server_world] = True
        match country_code:
            case "de":
                settings["groups"] = ["alle"]
            case "pl":
                settings["groups"] = ["wszystkie"]
            case "en":
                settings["groups"] = ["all"]
        settings["scheduler"]["ready_schedule"].clear()
        settings["coins"]["villages"].clear()

    def set_world_in_title() -> None:
        parent.entries_content["world_in_title"].set(
            f"{country_code.upper()}{world_number.upper()}"
        )

    def gui_update() -> None:
        parent.coins.redraw_choosed_villges()
        set_world_in_title()
        # Set combobox deafult values
        for combobox in (
            parent.farm.farm_group_A,
            parent.farm.farm_group_B,
            parent.farm.farm_group_C,
            parent.gathering.gathering_group,
            parent.control_panel.villages_groups,
        ):
            combobox["values"] = settings["groups"]
            combobox.set(settings["groups"][0])

    def update_settings_by_worlds_using_settings() -> None:
        parent.settings_by_worlds[server_world] = {}
        parent.settings_by_worlds[server_world].update(
            (k, v) for k, v in settings.items() if k != "globals"
        )

    if game_url == "tribalwars.net":
        country_code = "en"
    elif game_url == "divokekmeny.cz":
        country_code = "cs"
    else:
        country_code = game_url[game_url.rfind(".") + 1 :]
    server_world = f"{country_code}{world_number}"

    if not os.path.isdir("settings"):
        os.mkdir("settings")

    # Takie ustawienia już istnieją
    if server_world in parent.settings_by_worlds:
        if entry_change:
            parent.control_panel.show()
            custom_error(
                "Ustawienia tego świata już istnieją!",
                parent=parent.control_panel.master,
            )
            parent.entries_content["game_url"].set(settings["game_url"])
            parent.entries_content["world_number"].set(settings["world_number"])
            parent.control_panel.world_number_input.focus_set()
        else:
            custom_error(
                "Ustawienia tego świata już istnieją!",
                parent=parent.master.focus_displayof().winfo_toplevel(),
            )
        return False

    # Ustawienia pierwszego świata
    elif (len(parent.settings_by_worlds) == 0 and entry_change) or settings[
        "first_lunch"
    ]:
        if not get_world_config():
            return False
        set_additional_settings(
            game_url=game_url, country_code=country_code, server_world=server_world
        )
        gui_update()
        save_entry_to_settings(entries=parent.entries_content, settings=settings)
        update_settings_by_worlds_using_settings()
        parent.control_panel.game_url.config(bootstyle="default")
        parent.control_panel.world_number_input.config(bootstyle="default")
        if settings["first_lunch"]:
            parent.entries_content["game_url"].set(game_url)
            parent.entries_content["world_number"].set(world_number)
        return True

    # Zmiana świata w obrębie wybranej konfiguracji ustawień
    elif entry_change:
        if not get_world_config():
            return False
        del parent.settings_by_worlds[settings["server_world"]]
        if os.path.exists(f'settings/{settings["server_world"]}.json'):
            os.remove(f'settings/{settings["server_world"]}.json')
        set_additional_settings(
            game_url=game_url, country_code=country_code, server_world=server_world
        )
        gui_update()
        save_entry_to_settings(
            entries=parent.entries_content,
            settings=settings,
        )
        update_settings_by_worlds_using_settings()
        return True

    # Dodanie nowych ustawień nieistniejącego jeszcze świata
    else:

        def set_zero_to_tk_variables_in_entries(
            entries: dict | tk.Variable,
        ) -> None:
            """Ustawia domyślne wartości elementów GUI (entries_content)"""

            for key in entries:
                if isinstance(entries[key], dict):
                    if "globals" in key:
                        continue
                    set_zero_to_tk_variables_in_entries(entries=entries[key])
                else:
                    entries[key].set(0)

        # Save current entries to settings
        if settings["server_world"] in parent.settings_by_worlds:
            save_entry_to_settings(
                entries=parent.entries_content,
                settings=settings,
                settings_by_worlds=parent.settings_by_worlds,
            )
            parent.settings_by_worlds[settings["server_world"]] = deepcopy(settings)
            del parent.settings_by_worlds[settings["server_world"]]["globals"]
        else:
            save_entry_to_settings(entries=parent.entries_content, settings=settings)

        if not get_world_config():
            return False

        # Set and configure gui entries for new world
        set_zero_to_tk_variables_in_entries(entries=parent.entries_content)
        set_default_entries(entries=parent.entries_content)
        parent.entries_content["world_number"].set(value=world_number)
        parent.entries_content["game_url"].set(value=game_url)
        parent.entries_content["notifications"]["email_address"].set(
            value=parent.user_data["email"]
        )

        # Set settings for new world
        set_additional_settings(
            game_url=game_url, country_code=country_code, server_world=server_world
        )

        gui_update()
        invoke_checkbuttons(parent=parent.master, main_window=parent)
        parent.schedule.template_type.set("")

        save_entry_to_settings(entries=parent.entries_content, settings=settings)
        parent.settings_by_worlds[server_world] = deepcopy(settings)
        del parent.settings_by_worlds[server_world]["globals"]
        settings.update(parent.settings_by_worlds[server_world])

        return True
