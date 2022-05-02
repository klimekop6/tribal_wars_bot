import json
import logging
import os
import random
import re
import threading
import time
import traceback
from math import ceil, sqrt

import lxml.html
import requests
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

import email_notifications
from gui_functions import custom_error

logger = logging.getLogger(__name__)
if not os.path.exists("logs"):
    os.mkdir("logs")
f_handler = logging.FileHandler("logs/log.txt")
f_format = logging.Formatter(
    "\n%(levelname)s:%(name)s:%(asctime)s %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
)
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
logger.propagate = False


def attacks_labels(
    driver: webdriver.Chrome, settings: dict[str], notifications: bool = False
) -> bool:
    """Etykiety ataków"""

    COUNTRY_CODE: str = settings["country_code"]

    if not int(driver.execute_script("return window.game_data.player.incomings")):
        return False
    incomings = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "incomings_cell"))
    )  # Otwarcie karty z nadchodzącymi atakami
    driver.execute_script("return arguments[0].scrollIntoView(false);", incomings)
    top_bar_height = driver.find_element(By.XPATH, '//*[@id="ds_body"]/div[1]').size[
        "height"
    ]
    driver.execute_script(f"scrollBy(0, -{top_bar_height});")
    incomings.click()
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="paged_view_content"]/div[1]/*[@data-group-type="all"]')
        )
    ).click()  # Zmiana grupy na wszystkie
    manage_filters = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a'))
    )  # Zwraca element z filtrem ataków
    if (
        driver.find_element_by_xpath('//*[@id="paged_view_content"]/div[2]')
        .get_attribute("style")
        .find("display: none")
        != -1
    ):
        manage_filters.click()
    etkyieta_rozkazu = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[2]/td[2]/input',
            )
        )
    )
    etkyieta_rozkazu.clear()
    translate = {"pl": "Atak", "de": "Angriff"}
    etkyieta_rozkazu.send_keys(translate[COUNTRY_CODE])
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[6]/td/input',
            )
        )
    ).click()
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a'))
    )

    if not driver.find_elements(By.ID, "incomings_table"):
        return True

    element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "select_all"))
    )
    driver.execute_script("return arguments[0].scrollIntoView(true);", element)
    element.click()
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="incomings_table"]//input[@type="submit"]')
        )
    ).click()

    if notifications:
        etkyieta_rozkazu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[2]/td[2]/input',
                )
            )
        )
        etkyieta_rozkazu.clear()
        translate = {"pl": "Szlachcic", "de": "AG"}
        etkyieta_rozkazu.send_keys(translate[COUNTRY_CODE])
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[6]/td/input',
                )
            )
        ).click()
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a'))
        )
        if driver.find_elements_by_id("incomings_table"):
            number_of_attacks = driver.find_element_by_xpath(
                '//*[@id="incomings_table"]/tbody/tr[1]/th[1]'
            ).text
            number_of_attacks = re.search(r"\d+", number_of_attacks).group()
            reach_time_list = [
                reach_time.text
                for reach_time in driver.find_elements_by_xpath(
                    '//*[@id="incomings_table"]/tbody/tr/td[6]'
                )
            ]
            attacks_reach_time = "".join(
                f"{index+1}. {_}\n" for index, _ in enumerate(reach_time_list)
            )

            email_notifications.send_email(
                email_recepients=settings["notifications"]["email_address"],
                email_subject="Wykryto grubasy",
                email_body=f'Wykryto grubasy o godzinie {time.strftime("%H:%M:%S %d.%m.%Y", time.localtime())}\n\n'
                f"Liczba nadchodzących grubasów: {number_of_attacks}\n\n"
                f"Godziny wejść:\n"
                f"{attacks_reach_time}",
            )

            current_time = time.strftime("%H:%M:%S %d.%m.%Y", time.localtime())

            for label in driver.find_elements_by_xpath(
                '//*[@id="incomings_table"]/tbody/tr/td[1]/span/span/a[2]'
            ):
                driver.execute_script(
                    "return arguments[0].scrollIntoView(true);", label
                )
                label.click()

            for label_input in driver.find_elements_by_xpath(
                '//*[@id="incomings_table"]/tbody/tr/td[1]/span/span[2]/input[1]'
            ):
                label_input.clear()
                label_input.send_keys(f"szlachta notified {current_time}")
                label_input.send_keys(Keys.ENTER)

    return True


def auto_farm(driver: webdriver.Chrome, settings: dict[str]) -> None:
    """Automatyczne wysyłanie wojsk w asystencie farmera"""

    # Przechodzi do asystenta farmera
    WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.ID, "manager_icon_farm"))
    ).click()

    # Sprawdza czy znajduję się w prawidłowej grupie jeśli nie to przechodzi do prawidłowej -> tylko dla posiadaczy konta premium
    if (
        driver.execute_script("return premium")
        and int(driver.execute_script("return game_data.player.villages")) > 1
    ):
        open_groups = driver.find_element_by_id("open_groups")
        driver.execute_script("arguments[0].scrollIntoView(false);", open_groups)
        open_groups.click()
        current_group = (
            WebDriverWait(driver, 10, 0.033)
            .until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="group_id"]/option[@selected="selected"]')
                )
            )
            .text
        )
        # Check and change group if not in proper one
        if current_group != settings["farm_group"]:
            select = Select(driver.find_element_by_id("group_id"))
            select.select_by_visible_text(settings["farm_group"])
            WebDriverWait(driver, 10, 0.033).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="group_table"]/tbody/tr[1]/td[1]/a')
                )
            ).click()
        close_groups = WebDriverWait(driver, 3, 0.033).until(
            EC.presence_of_element_located((By.ID, "closelink_group_popup"))
        )
        driver.execute_script(
            "return arguments[0].scrollIntoView(false);", close_groups
        )
        close_groups.click()
        WebDriverWait(driver, 2, 0.033).until(  # Wait for group_popup close
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="close_groups"][@style="display: none;"]')
            )
        )
        # Go to the first village in choosed group if not in proper one
        first_in_group = driver.find_elements(
            By.XPATH, '//*[@id="menu_row2"]/td[1]/span/a'
        )
        if first_in_group:
            first_in_group[0].click()

    # Lista wykorzystanych wiosek - unikalne id wioski'
    used_villages = []
    used_villages.append(driver.execute_script("return window.game_data.village.id;"))

    # Główna pętla funkcji
    while True:

        # Ukrywa chat
        chat = driver.find_element_by_xpath('//*[@id="chat-wrapper"]')
        driver.execute_script("arguments[0].innerHTML = '';", chat)

        # Szablon A i B nazwy jednostek i ich liczebność
        doc = lxml.html.fromstring(
            driver.find_element_by_id("content_value").get_attribute("innerHTML")
        )
        template_troops = {
            "A": doc.xpath("div[2]/div/form/table/tbody/tr[2]/td/input"),
            "B": doc.xpath("div[2]/div/form/table/tbody/tr[4]/td/input"),
        }

        for key in template_troops:
            tmp = {}
            for row in template_troops[key]:
                troop_number = int(row.get("value"))
                if troop_number:
                    troop_name = row.get("name")
                    troop_name = re.search(r"[a-z]+", troop_name).group()
                    tmp[troop_name] = troop_number
            template_troops[key] = tmp

        # Unikalne nazwy jednostek z szablonów A i B
        troops_name = set(
            _key for key in template_troops for _key in template_troops[key].keys()
        )

        # Aktualnie dostępne jednostki w wiosce
        doc = doc.xpath('//*[@id="units_home"]/tbody/tr[2]')[0]
        available_troops = {
            troop_name: int(doc.xpath(f'td[@id="{troop_name}"]')[0].text)
            for troop_name in troops_name
        }

        # Pomija wioskę jeśli nie ma z niej nic do wysłania
        skip = {"A": False, "B": False}
        for template in template_troops:
            for troop_name, troop_number in template_troops[template].items():
                if available_troops[troop_name] - troop_number < 0:
                    skip[template] = True
                    break

        if skip["A"] and skip["B"]:
            ActionChains(driver).send_keys("d").perform()
            if (
                driver.execute_script("return window.game_data.village.id;")
                in used_villages
            ):
                break
            used_villages.append(
                driver.execute_script("return window.game_data.village.id;")
            )
            continue

        # Lista poziomów murów
        walls_level = (
            driver.find_element_by_id("plunder_list")
            .get_attribute("innerHTML")
            .split("<tr")[3:]
        )
        for index, row in enumerate(walls_level):
            walls_level[index] = row.split("<td")[7:8]
        for index, row in enumerate(walls_level):
            for ele in row:
                walls_level[index] = ele[ele.find(">") + 1 : ele.find("<")]
        walls_level = [ele if ele == "?" else int(ele) for ele in walls_level]

        # Lista przycisków do wysyłki szablonów A, B i C
        villages_to_farm = {}

        if int(settings["A"]["active"]):
            villages_to_farm["A"] = 9  # Szablon A
        if int(settings["B"]["active"]):
            villages_to_farm["B"] = 10  # Szablon B
        if int(settings["C"]["active"]):
            villages_to_farm["C"] = 11  # Szablon C

        # Wysyłka wojsk w asystencie farmera
        start_time = 0
        no_units = False
        for index, template in enumerate(villages_to_farm):

            if skip[template]:
                continue

            villages_to_farm[template] = driver.find_elements_by_xpath(
                f'//*[@id="plunder_list"]/tbody/tr/td[{villages_to_farm[template]}]/a'
            )
            captcha_solved = False
            for village, wall_level in zip(villages_to_farm[template], walls_level):
                if isinstance(wall_level, str) and not int(
                    settings[template]["wall_ignore"]
                ):
                    continue

                if int(settings[template]["wall_ignore"]) or int(
                    settings[template]["min_wall"]
                ) <= wall_level <= int(settings[template]["max_wall"]):
                    for unit, number in template_troops[template].items():
                        if available_troops[unit] - number < 0:
                            no_units = True
                            break
                        available_troops[unit] -= number
                    if no_units:
                        break

                    send_troops_in_the_middle(driver=driver, settings=settings)

                    if not captcha_solved:
                        captcha_check(driver=driver, settings=settings)
                        captcha_solved = True

                    while time.time() - start_time < 0.195:
                        time.sleep(0.01)
                    driver.execute_script(
                        'return arguments[0].scrollIntoView({block: "center"});',
                        village,
                    )
                    village.click()
                start_time = time.time()

            if index < len(villages_to_farm) - 1:
                no_units = False
                driver.refresh()
                chat = driver.find_element_by_xpath('//*[@id="chat-wrapper"]')
                driver.execute_script("arguments[0].innerHTML = '';", chat)

        # Przełącz wioskę i sprawdź czy nie jest to wioska startowa
        ActionChains(driver).send_keys("d").perform()
        if (
            driver.execute_script("return window.game_data.village.id;")
            in used_villages
        ):
            break
        used_villages.append(
            driver.execute_script("return window.game_data.village.id;")
        )


def captcha_check(
    driver: webdriver.Chrome, settings: dict[str], page_source: str = None
) -> None:
    """Check for captcha existence.

    If exist, wait until solved and than update captcha counter.
    """

    if not page_source:
        page_source = driver.page_source

    if page_source.find("captcha") != -1:
        WebDriverWait(driver, 120).until(
            lambda x: x.find_element_by_css_selector(".antigate_solver.solved")
        )
        settings["temp"]["captcha_counter"].set(
            settings["temp"]["captcha_counter"].get() + 1
        )


def check_groups(
    driver: webdriver.Chrome, settings: dict[str], run_driver, *args
) -> None:
    """Sprawdza dostępne grupy i zapisuje je w settings.json"""

    tmp_driver = False
    if not driver:
        driver = run_driver(settings=settings)
        log_in(driver, settings)
        tmp_driver = True

    logged_in = True
    if f"{settings['server_world']}.{settings['game_url']}" not in driver.current_url:
        logged_in = False
        driver.get(
            f"https://www.{settings['game_url']}/page/play/{settings['server_world']}"
        )

    if not driver.execute_script("return premium"):
        if tmp_driver:
            driver.quit()

        if not logged_in:
            driver.get("chrome://newtab")

        for combobox in args:
            combobox["values"] = ["Grupy niedostępne"]
            combobox.set("Grupy niedostępne")

        return

    driver.find_element_by_id("open_groups").click()
    groups = (
        WebDriverWait(driver, 10, 0.033)
        .until(EC.presence_of_element_located((By.ID, "group_id")))
        .get_attribute("innerHTML")
    )
    driver.find_element_by_id("close_groups").click()
    groups = [group[1:-1] for group in re.findall(r">[^<].+?<", groups)]
    settings["groups"].clear()
    settings["groups"].extend(groups)
    for combobox in args:
        combobox["values"] = settings["groups"]
        combobox.set("Wybierz grupę")

    if tmp_driver:
        driver.quit()

    if not logged_in:
        driver.get("chrome://newtab")


def cut_time(driver: webdriver.Chrome) -> None:
    """Finish construction time by using free available speed up"""


def dodge_attacks(driver: webdriver.Chrome) -> None:
    """Unika wybranej wielkości offów"""

    villages = player_villages(driver)

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "incomings_cell"))
    ).click()  # Przełącz do strony nadchodzących ataków
    manage_filters = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a'))
    )  # Filtr ataków
    if (
        driver.find_element_by_xpath('//*[@id="paged_view_content"]/div[2]')
        .get_attribute("style")
        .find("display: none")
        != -1
    ):  # Czy włączony
        manage_filters.click()  # Włącz filtr ataków
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[2]/td[2]/input',
            )
        )
    ).clear()  # Etykieta rozkazu
    attack_size = input("1 all\n" "2 small\n" "3 medium\n" "4 big")
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                f'//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[6]/td/label[{attack_size}]/input',
            )
        )
    ).click()  # Wielkość idących wojsk
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[7]/td/input',
            )
        )
    ).click()  # Zapisz i przeładuj
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a'))
    )  # Sprawdź widoczność przycisku "zarządzanie filtrami"
    try:
        driver.find_element_by_id(
            "incomings_table"
        )  # Czy są ataki spełniające powyższe kryteria
    except:
        pass

    targets = driver.find_elements_by_xpath(
        '//*[@id="incomings_table"]/tbody/tr/td[2]/a'
    )
    dates = driver.find_elements_by_xpath('//*[@id="incomings_table"]/tbody/tr/td[6]')

    date_time = time.gmtime()

    targets = [target.get_attribute("href") for target in targets]
    dates = [data.text for data in dates]

    for index, date in enumerate(dates):
        if date.startswith("dzisiaj"):
            dates[index] = date.replace(
                "dzisiaj o",
                f"{date_time.tm_mday}.{date_time.tm_mon :>02}.{date_time.tm_year}",
            )[:-4]
        elif date.startswith("jutro o"):
            dates[index] = date.replace(
                "jutro o",
                f"{date_time.tm_mday+1}.{date_time.tm_mon :>02}.{date_time.tm_year}",
            )[:-4]
        else:
            dates[index] = date.replace("dnia ", "").replace(
                ". o", f".{date_time.tm_year}"
            )[:-4]

    dates = [time.mktime(time.strptime(date, "%d.%m.%Y %H:%M:%S")) for date in dates]
    targets = [target.replace("overview", "place") for target in targets]

    while True:
        search_for = villages["coords"][
            villages["id"].index(
                targets[0][targets[0].find("=") + 1 : targets[0].find("&")]
            )
        ]
        nearest = sorted(
            [
                [
                    sqrt(
                        pow(int(search_for[:3]) - int(village[:3]), 2)
                        + pow(int(search_for[4:]) - int(village[4:]), 2)
                    ),
                    index,
                ]
                for index, village in enumerate(villages["coords"])
            ]
        )[1][1]
        targets[0] += "&target=" + villages["id"][nearest]
        while True:
            if time.time() > dates[0] - 5:
                driver.get(targets[0])
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "selectAllUnits"))
                ).click()
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "target_support"))
                ).click()
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "troop_confirm_go"))
                ).click()
                send_time = time.time()
                break_attack = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "command-cancel"))
                )
                time.sleep(((dates[0] - send_time) / 2) + 1)
                driver.get(break_attack.get_attribute("href"))
                del dates[0], targets[0]
                break


def gathering_resources(driver: webdriver.Chrome, **kwargs) -> list:
    """Wysyła wojska do zbierania surowców"""

    settings = kwargs["settings"]

    if "url_to_gathering" not in kwargs:
        # Tworzy listę docelowo zawierającą słowniki
        list_of_dicts = []

        # Przejście do prawidłowej grupy -> tylko dla posiadaczy konta premium
        if (
            driver.execute_script("return premium")
            and int(driver.execute_script("return game_data.player.villages")) > 1
        ):
            groups_popup = driver.find_element(By.ID, "open_groups")
            driver.execute_script("arguments[0].scrollIntoView(false);", groups_popup)
            groups_popup.click()
            current_group = (
                WebDriverWait(driver, 10, 0.033)
                .until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//*[@id="group_id"]/option[@selected="selected"]')
                    )
                )
                .text
            )

            if current_group != settings["gathering_group"]:
                select = Select(driver.find_element_by_id("group_id"))
                select.select_by_visible_text(settings["gathering_group"])
                WebDriverWait(driver, 3, 0.025).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//*[@id="group_table"]/tbody/tr[1]/td[1]/a')
                    )
                ).click()
            close_group = WebDriverWait(driver, 3, 0.025).until(
                EC.element_to_be_clickable((By.ID, "closelink_group_popup"))
            )
            driver.execute_script(
                "return arguments[0].scrollIntoView(true);", close_group
            )
            close_group.click()
            WebDriverWait(driver, 2, 0.033).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="close_groups"][@style="display: none;"]')
                )
            )
            # Go to the first village in choosed group if not in proper one
            first_in_group = driver.find_elements(
                By.XPATH, '//*[@id="menu_row2"]/td[1]/span/a'
            )
            if first_in_group:
                first_in_group[0].click()

        # Przejście do ekranu zbieractwa na placu
        current_village_id = driver.execute_script("return window.game_data.village.id")
        url = driver.current_url
        base_url = url[: url.rfind("/")]
        url = (
            base_url
            + f"/game.php?village={current_village_id}&screen=place&mode=scavenge"
        )
        driver.get(url)

        # Początkowa wioska
        starting_village = driver.execute_script("return window.game_data.village.id;")
    else:
        driver.get(kwargs["url_to_gathering"])

    footer_height = driver.find_element(By.ID, "footer").size["height"]

    # Core całej funkcji, kończy gdy przejdzie przez wszystkie wioski
    while True:

        send_troops_in_the_middle(driver=driver, settings=settings)

        page_source = driver.page_source
        captcha_check(driver=driver, settings=settings, page_source=page_source)

        # Skip to next village if current one doesn't have place
        place_str = re.search(r'"place":"\d"', page_source).group()
        if re.search(r"\d", place_str).group() == "0":
            driver.find_element_by_id("ds_body").send_keys("d")
            current_village_id = driver.execute_script(
                "return window.game_data.village.id;"
            )
            if starting_village == current_village_id:
                return list_of_dicts
            continue

        # Dostępne wojska
        available_troops = {}
        doc = lxml.html.fromstring(page_source)
        troops_name = [
            troop_name.get("name")
            for troop_name in doc.xpath(
                '//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/input'
            )
        ]
        troops_number = [
            troop_number.text
            for troop_number in doc.xpath(
                '//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/a'
            )
        ][:-1]

        # Zapobiega wczytaniu pustego kodu źródłowego - gdy driver.page_source zwróci pusty lub nieaktulny kod HTML
        if not troops_name:
            for _ in range(50):
                time.sleep(0.05)
                doc = lxml.html.fromstring(driver.page_source)
                troops_name = [
                    troop_name.get("name")
                    for troop_name in doc.xpath(
                        '//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/input'
                    )
                ]
                troops_number = [
                    troop_number.text
                    for troop_number in doc.xpath(
                        '//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/a'
                    )
                ][:-1]
                if troops_name:
                    break

        for troop_name, troop_number in zip(troops_name, troops_number):
            if (
                int(settings["gathering_troops"][troop_name]["use"])
                and int(troop_number[1:-1]) > 0
            ):
                available_troops[troop_name] = int(troop_number[1:-1]) - int(
                    settings["gathering_troops"][troop_name]["left_in_village"]
                )
                if available_troops[troop_name] > int(
                    settings["gathering_troops"][troop_name]["send_max"]
                ):
                    available_troops[troop_name] = int(
                        settings["gathering_troops"][troop_name]["send_max"]
                    )

        # Odblokowane i dostępne poziomy zbieractwa
        troops_to_send = {
            1: {"capacity": 1},
            2: {"capacity": 0.4},
            3: {"capacity": 0.2},
            4: {"capacity": 4 / 30},
        }
        for number, row in enumerate(
            zip(
                doc.xpath('//*[@id="scavenge_screen"]/div/div[2]/div/div[3]/div'),
                (
                    int(settings["gathering"]["ommit"][ele])
                    for ele in settings["gathering"]["ommit"]
                ),
            )
        ):
            if row[0].get("class") != "inactive-view" or row[1]:
                del troops_to_send[number + 1]

        # Ukrywa chat
        chat = driver.find_element_by_xpath('//*[@id="chat-wrapper"]')
        driver.execute_script("arguments[0].innerHTML = '';", chat)

        # Tymaczsowy zapis w celu wykrycia problemów z wysyłką
        # class_list = [ele.get('class') for ele in doc.xpath('//*[@id="scavenge_screen"]/div/div[2]/div/div[3]/div')]
        # current_village_name = driver.find_element_by_xpath('//*[@id="menu_row2_village"]/a').text
        # if 'url_to_gathering' in kwargs:
        #     gathering_info_file = open('gathering_info.txt', 'a')
        #     gathering_info_file.write(
        #         f'{time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())}\n'
        #         f'{current_village_name}\n'
        #         f'available_troops {available_troops}\n'
        #         f'troops_to_send {troops_to_send}\n'
        #         f'{class_list}\n\n')
        #     gathering_info_file.close()

        # Obliczenie i wysyłanie wojsk na zbieractwo
        sum_capacity = sum(troops_to_send[key]["capacity"] for key in troops_to_send)
        units_capacity = {
            "spear": 25,
            "sword": 15,
            "axe": 10,
            "archer": 10,
            "light": 80,
            "marcher": 50,
            "heavy": 50,
            "knight": 100,
        }
        reduce_ratio = None
        max_resources = int(settings["gathering_max_resources"])
        round_ups_per_troop = {troop_name: 0 for troop_name in available_troops}
        for key in troops_to_send:
            for troop_name, troop_number in available_troops.items():
                counted_troops_number = (
                    troops_to_send[key]["capacity"] / sum_capacity * troop_number
                )
                if (counted_troops_number % 1) > 0.5 and round_ups_per_troop[
                    troop_name
                ] < 1:
                    troops_to_send[key][troop_name] = round(counted_troops_number)
                    round_ups_per_troop[troop_name] += 1
                else:
                    troops_to_send[key][troop_name] = int(counted_troops_number)
            if not reduce_ratio:
                sum_troops_capacity = (
                    sum(
                        [
                            troops_to_send[key][troop_name] * units_capacity[troop_name]
                            if troops_to_send[key][troop_name] > 0
                            else 0
                            for troop_name in available_troops
                        ]
                    )
                    / 10
                    / troops_to_send[key]["capacity"]
                )
                if sum_troops_capacity > max_resources:
                    reduce_ratio = max_resources / sum_troops_capacity
                else:
                    reduce_ratio = 1
            for troop_name in available_troops:
                if troops_to_send[key][troop_name] > 0:
                    _input = WebDriverWait(driver, 3, 0.01).until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                f'//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/input[@name="{troop_name}"]',
                            )
                        )
                    )
                    try:
                        _input.click()
                    except:
                        driver.execute_script(
                            "return arguments[0].scrollIntoView(true);", _input
                        )
                        top_bar_height = driver.find_element(
                            By.XPATH, '//*[@id="ds_body"]/div[1]'
                        ).size["height"]
                        driver.execute_script(f"scrollBy(0, -{top_bar_height})")
                        _input.click()
                    _input.clear()
                    if reduce_ratio != 1:
                        _input.send_keys(
                            round(troops_to_send[key][troop_name] * reduce_ratio)
                        )
                    else:
                        _input.send_keys(troops_to_send[key][troop_name])
            army_sum = 0
            for troop_name in available_troops:
                if troops_to_send[key][troop_name] > 0:
                    match troop_name:
                        case "light":
                            army_sum += troops_to_send[key]["light"] * 4 * reduce_ratio
                        case "marcher":
                            army_sum += (
                                troops_to_send[key]["marcher"] * 5 * reduce_ratio
                            )
                        case "heavy":
                            army_sum += troops_to_send[key]["heavy"] * 6 * reduce_ratio
                        case "knight":
                            army_sum += (
                                troops_to_send[key]["knight"] * 10 * reduce_ratio
                            )
                        case _:
                            army_sum += troops_to_send[key][troop_name] * reduce_ratio
            if army_sum < 10:
                if key == 1:
                    troops_to_send.clear()
                break
            start = WebDriverWait(driver, 3, 0.01).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f'//*[@id="scavenge_screen"]/div/div[2]/div[{key}]/div[3]/div/div[2]/a[1]',
                    )
                )
            )
            driver.execute_script("return arguments[0].scrollIntoView(false);", start)
            driver.execute_script(f"scrollBy(0, {footer_height});")
            start.click()
            WebDriverWait(driver, 3, 0.025).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f'//*[@id="scavenge_screen"]/div/div[2]/div[{key}]/div[3]/div/ul/li[4]/span[@class="return-countdown"]',
                    )
                )
            )

        # tymczasowo w celu zlokalizowania problemu
        # if 'url_to_gathering' in kwargs:
        # logging.error(f'available_troops {available_troops}\ntroops_to_send {troops_to_send}')

        if "url_to_gathering" in kwargs:

            # Zwraca docelowy url i czas zakończenia zbieractwa w danej wiosce
            doc = lxml.html.fromstring(
                driver.find_element_by_xpath(
                    '//*[@id="scavenge_screen"]/div/div[2]'
                ).get_attribute("innerHTML")
            )
            doc = doc.xpath("//div/div[3]/div/ul/li[4]/span[2]")
            if troops_to_send and not [ele.text for ele in doc]:
                for _ in range(10):
                    time.sleep(0.2)
                    doc = lxml.html.fromstring(
                        driver.find_element_by_xpath(
                            '//*[@id="scavenge_screen"]/div/div[2]'
                        ).get_attribute("innerHTML")
                    )
                    doc = doc.xpath("//div/div[3]/div/ul/li[4]/span[2]")
                    if [ele.text for ele in doc]:
                        break
            try:
                journey_time = [
                    int(_) for _ in max([ele.text for ele in doc]).split(":")
                ]
            except:
                journey_time = [
                    0,
                    30,
                    0,
                ]  # Ponowna próba wysyłki wojsk na zbieractwo za 30min
            journey_time = (
                journey_time[0] * 3600 + journey_time[1] * 60 + journey_time[2]
            )
            return [
                {
                    "func": "gathering",
                    "url_to_gathering": kwargs["url_to_gathering"],
                    "start_time": time.time() + journey_time + 3,
                    "server_world": settings["server_world"],
                    "settings": settings,
                    "errors_number": 0,
                }
            ]

        # Tworzy docelowy url i czas zakończenia zbieractwa w danej wiosce
        div_scavenge: WebElement = WebDriverWait(driver, 3, 0.025).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="scavenge_screen"]/div/div[2]')
            )
        )
        doc = lxml.html.fromstring(div_scavenge.get_attribute("innerHTML"))
        doc = doc.xpath("//div/div[3]/div/ul/li[4]/span[2]")
        try:
            journey_time = [int(_) for _ in max([ele.text for ele in doc]).split(":")]
        except:
            # Pomija wioski z zablokowanym zbieractwem
            driver.find_element_by_id("ds_body").send_keys("d")
            current_village_id = driver.execute_script(
                "return window.game_data.village.id;"
            )
            if starting_village == current_village_id:
                return list_of_dicts
            continue
        journey_time = journey_time[0] * 3600 + journey_time[1] * 60 + journey_time[2]
        list_of_dicts.append(
            {
                "func": "gathering",
                "url_to_gathering": base_url
                + f"/game.php?village={current_village_id}&screen=place&mode=scavenge",
                "start_time": time.time() + journey_time + 3,
                "server_world": settings["server_world"],
                "settings": settings,
                "errors_number": 0,
            }
        )

        # Przełącz wioskę i sprawdź czy nie jest to wioska startowa jeśli tak zwróć listę słowników z czasem i linkiem do poszczególnych wiosek
        driver.find_element_by_id("ds_body").send_keys("d")
        current_village_id = driver.execute_script(
            "return window.game_data.village.id;"
        )
        if starting_village == current_village_id:
            return list_of_dicts


def get_villages_id(settings: dict[str], update: bool = False) -> dict:
    """Download, process and save in text file for future use.
    In the end return all villages in the world with proper id.
    """

    def update_file() -> None:
        """Create or update file with villages and their id's"""

        url = (
            f"http://{settings['server_world']}.{settings['game_url']}/map/village.txt"
        )
        response = requests.get(url)
        response = response.text
        response = response.splitlines()
        villages = {}
        for row in response:
            id, _, x, y, _, _, _ = row.split(",")
            villages[x + "|" + y] = id

        try:
            world_villages_file = open(f'villages{settings["server_world"]}.txt', "w")
        except:
            logger.error(
                f'There was a problem with villages{settings["server_world"]}.txt'
            )
        else:
            for village_coords, village_id in villages.items():
                world_villages_file.write(f"{village_coords},{village_id}\n")
        finally:
            world_villages_file.close()

    if update:
        update_file()

    villages = {}
    try:
        world_villages_file = open(f'villages{settings["server_world"]}.txt')
    except FileNotFoundError:
        update_file()
        world_villages_file = open(f'villages{settings["server_world"]}.txt')
    else:
        for row in world_villages_file:
            village_coords, village_id = row.split(",")
            villages[village_coords] = village_id
    finally:
        world_villages_file.close()

    return villages


def log_error(driver: webdriver.Chrome, msg: str = "") -> None:
    """Write erros with traceback into logs/log.txt"""

    driver.save_screenshot(
        f'logs/{time.strftime("%d.%m.%Y %H_%M_%S", time.localtime())}.png'
    )
    error_str = traceback.format_exc()
    error_str = error_str[: error_str.find("Stacktrace")]
    logger.error(
        f"\n\n{msg}\n\n"
        f"{driver.current_url}\n\n"
        f"{error_str}\n"
        f"-----------------------------------------------------------------------------------\n"
    )


def log_in(driver: webdriver.Chrome, settings: dict) -> bool:
    """Logowanie"""

    try:
        driver.get(
            f"https://www.{settings['game_url']}/page/play/{settings['server_world']}"
        )

        # Czy prawidłowo wczytano i zalogowano się na stronie
        if f"{settings['server_world']}.{settings['game_url']}" in driver.current_url:
            return True

        # Ręczne logowanie na stronie plemion
        elif f"https://www.{settings['game_url']}/" == driver.current_url:

            if not "game_user_name" in settings:
                driver.switch_to.window(driver.current_window_handle)
                custom_error(
                    message="Zaloguj się na otwartej stronie plemion.\n"
                    "Pole zapamiętaj mnie powinno być zaznaczone."
                )
                if WebDriverWait(driver, 60).until(
                    EC.invisibility_of_element_located((By.ID, "login_form"))
                ):
                    return log_in(driver=driver, settings=settings)

            username = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="username"]'))
            )
            password = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="password"]'))
            )

            username.send_keys(Keys.CONTROL + "a")
            username.send_keys(Keys.DELETE)
            password.send_keys(Keys.CONTROL + "a")
            password.send_keys(Keys.DELETE)
            username.send_keys(settings["game_user_name"])
            password.send_keys(settings["game_user_password"])

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "btn-login"))
            ).click()
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f'//span[text()="Świat {settings["world_number"]}"]')
                )
            ).click()
            return True

        # Ponowne wczytanie strony w przypadku niepowodzenia (np. chwilowy brak internetu)
        else:
            for sleep_time in (5, 15, 60, 120, 300):
                time.sleep(sleep_time)
                driver.get(
                    f"https://www.{settings['game_url']}/page/play/{settings['server_world']}"
                )
                if (
                    f"{settings['server_world']}.{settings['game_url']}"
                    in driver.current_url
                ):
                    return True

        log_error(driver, msg="bot_functions -> log_in no error raised")
        return False

    except BaseException:
        log_error(driver, msg="bot_functions -> log_in error raised")
        return False


def market_offers(driver: webdriver.Chrome) -> None:
    """Wystawianie offert tylko dla plemienia"""

    current_village_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="menu_row2_village"]/a'))
    )
    summary_production = (
        current_village_link.get_attribute("href") + "_villages&mode=prod"
    )
    driver.get(summary_production)

    villages_resources = {"villages": [], "resources": [], "summary": []}
    villages_resources["villages"] = [
        village_resources.get_attribute("href").replace(
            "overview", "market&mode=own_offer"
        )
        for village_resources in driver.find_elements_by_xpath(
            '//*[@id="production_table"]/tbody/tr/td[2]/span/span/a[1]'
        )
    ]
    resources = [
        int(resource.text.replace(".", ""))
        for resource in driver.find_elements_by_xpath(
            '//*[@id="production_table"]/tbody/tr/td[4]/span'
        )
    ]
    villages_resources["resources"] = [
        [resources[index], resources[index + 1], resources[index + 2]]
        for index in range(0, len(resources), 3)
    ]

    for i in range(3):
        villages_resources["summary"].extend(
            [sum([resource[i] for resource in villages_resources["resources"]])]
        )
    offer = villages_resources["summary"].index(max(villages_resources["summary"]))
    need = villages_resources["summary"].index(min(villages_resources["summary"]))

    for (village, resource) in zip(
        villages_resources["villages"], villages_resources["resources"]
    ):
        if resource[need] < 20000 and resource[offer] > 100000:
            driver.get(village)
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f'//*[@id="res_buy_selection"]/label[{need+1}]/input')
                )
            ).click()
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f'//*[@id="res_sell_selection"]/label[{offer+1}]/input')
                )
            ).click()
            how_many = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//*[@id="own_offer_form"]/table[3]/tbody/tr[2]/td[2]/input',
                    )
                )
            )
            max_to_use = int((resource[offer] - 100000) / 1000)
            if max_to_use < int(how_many.get_attribute("value")):
                how_many.clear()
                how_many.send_keys(str(max_to_use))
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//*[@id="own_offer_form"]/table[3]/tbody/tr[4]/td[2]/label/input',
                    )
                )
            )
            driver.execute_script("return arguments[0].scrollIntoView(true);", element)
            element.click()
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="submit_offer"]'))
            )
            driver.execute_script("return arguments[0].scrollIntoView(true);", element)
            element.click()
        else:
            continue


def mark_villages_on_map(driver: webdriver.Chrome) -> None:
    """Zaznacza na mapie wioski spełniające konkretne kryteria na podstawie przeglądów plemiennych"""

    villages_to_mark = []
    url = driver.current_url
    village_id = url[url.find("=") + 1 : url.find("&")]
    url = (
        url[: url.find("?") + 1]
        + "screen=ally&mode=members_defense&player_id=&village="
        + village_id
    )
    player_name = driver.find_element_by_xpath(
        '//*[@id="menu_row"]/td[11]/table/tbody/tr[1]/td/a'
    ).get_attribute("innerHTML")
    current_player_id = driver.find_element_by_xpath(
        f'//*[@id="ally_content"]/div/form/select/option[contains(text(), "{player_name}")]'
    ).get_attribute("value")
    player_id = [
        player_id.get_attribute("value")
        for player_id in driver.find_elements_by_xpath(
            '//*[@id="ally_content"]/div/form/select/option'
        )
    ][1:]
    del player_id[player_id.index(str(current_player_id))]
    for id in player_id:
        driver.get(url[: url.find("player_id") + 10] + id + url[url.rfind("&") :])
        if not driver.find_elements_by_xpath(
            '//*[@id="ally_content"]/div/div'
        ):  # Omija graczy bez wiosek
            continue
        village_number = len(
            driver.find_elements_by_xpath(
                '//*[@id="ally_content"]/div/div/table/tbody/tr/td[1]'
            )
        )
        tmp1 = driver.find_element_by_xpath(
            '//*[@id="ally_content"]/div/div/table/tbody'
        ).text
        if (
            tmp1.find("?") != -1
        ):  # Omija graczy którzy nie udostępniają podglądu swoich wojsk
            continue
        tmp1 = [tmp[tmp.find(" w wiosce ") + 10 :] for tmp in tmp1.splitlines()[1::2]]
        tmp1 = [tmp.split() for tmp in tmp1]
        for index in range(len(tmp1)):
            tmp1[index].insert(0, index * 2 + 2)
        index = 0
        while index < len(tmp1):
            if sum([int(cell) for cell in tmp1[index][1:]]) > 100:
                del tmp1[index]
                continue
            index += 1
        for index in range(len(tmp1)):
            tmp1[index][0] = driver.find_element_by_xpath(
                f'//*[@id="ally_content"]/div/div/table/tbody/tr[{tmp1[index][0]}]/td[1]/a'
            ).get_attribute("href")
        villages_to_mark.extend([to_mark[0] for to_mark in tmp1])

    for village_to_mark in villages_to_mark:
        driver.get(village_to_mark)
        driver.find_element_by_xpath(
            '//*[@id="content_value"]/table/tbody/tr/td[1]/table[2]/tbody/tr[8]'
        ).click()  # Otwiera zarządzanie zaznaczeniami mapy
        WebDriverWait(driver, 10, 0.1).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="map_color_assignment"]/form[1]/table/tbody/tr[4]/td/input',
                )
            )
        )  # Czeka na załadowanie kodu HTML
        groups = [
            label_name.text
            for label_name in driver.find_elements_by_xpath(
                '//*[@id="map_group_management"]/table/tbody/tr/td/label'
            )
        ]  # Dostępne grupy zaznaczeń na mapie
        group_name = "FARMA"  # Nazwa wybranej grupy
        element = driver.find_element_by_xpath(
            f'//*[@id="map_group_management"]/table/tbody/tr[{groups.index(group_name)+1}]/td/label/input'
        )  # Klika wybraną nazwę grupy
        driver.execute_script("return arguments[0].scrollIntoView(true);", element)
        element.click()
        element = driver.find_element_by_xpath(
            '//*[@id="map_group_management"]/table/tbody/tr/td/input[@value="Zapisz"]'
        )  # Zapisuję wybór
        driver.execute_script("return arguments[0].scrollIntoView(true);", element)
        element.click()


def player_villages(driver: webdriver.Chrome) -> dict:
    """Tworzy i zwraca słownik z id i koordynatami wiosek gracza"""

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="menu_row"]/td[11]/a'))
    ).click()
    village_number = (
        WebDriverWait(driver, 10)
        .until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="villages_list"]/thead/tr/th[1]')
            )
        )
        .text
    )
    village_number = int(village_number[village_number.find("(") + 1 : -1])
    if village_number > 100:
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="villages_list"]/tbody/tr[101]/td/a')
            )
        )
        driver.execute_script("return arguments[0].scrollIntoView(true);", element)
        element.click()
        WebDriverWait(driver, 10, 0.1).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="villages_list"]/tbody/tr[101]/td[3]')
            )
        )

    villages = {
        "id": [
            id.get_attribute("data-id")
            for id in driver.find_elements_by_xpath(
                '//*[@id="villages_list"]/tbody/tr/td[1]/table/tbody/tr/td[1]/span'
            )
        ],
        "coords": [
            coords.text
            for coords in driver.find_elements_by_xpath(
                '//*[@id="villages_list"]/tbody/tr/td[3]'
            )
        ],
    }

    return villages


def premium_exchange(driver: webdriver.Chrome, settings: dict) -> None:
    """Umożliwia automatyczną sprzedaż lub zakup surwców za punkty premium"""

    up_to_date = False
    if "villages_update_time" in settings["temp"]:
        if time.time() - settings["temp"]["villages_update_time"] < 3600:
            villages = settings["temp"]["villages"]
            up_to_date = True

    # Update villages list if cached more than one hour ago
    if not up_to_date:
        current_village_id = int(
            driver.execute_script("return window.game_data.village.id")
        )
        url = driver.current_url
        url = url[: url.rfind("/")]
        player_profile_url = (
            url + f"/game.php?village={current_village_id}&screen=info_player"
        )

        try:
            html_response = driver.execute_script(
                f"""
                var request = new XMLHttpRequest();
                request.open("GET", "{player_profile_url}", false);
                request.send(null);   
                return request.responseText;"""
            )
        except BaseException:
            log_in(driver=driver, settings=settings)
            html_response = driver.execute_script(
                f"""
                var request = new XMLHttpRequest();
                request.open("GET", "{player_profile_url}", false);
                request.send(null);   
                return request.responseText;"""
            )
        doc = lxml.html.fromstring(html_response)
        doc = doc.xpath('//table[@id="villages_list"]/tbody/tr')
        if len(doc) > 100:
            player_id = driver.execute_script("return game_data.player.id")
            get_remain_villages_url = (
                f"{player_profile_url}&ajax=fetch_villages&player_id={player_id}"
            )
            html_response = driver.execute_script(
                f"""
                var request = new XMLHttpRequest();
                request.open("GET", "{get_remain_villages_url}", false);
                request.send(null);   
                return request.responseText;"""
            )
            add_to_doc = lxml.html.fromstring(json.loads(html_response)["villages"])
            doc.pop()
            doc.extend(add_to_doc)

        villages = {}
        for row in doc:
            village_id = row.xpath("td/table/tr/td/span")[0].get("data-id")
            village_url = (
                url + f"/game.php?village={village_id}&screen=market&mode=exchange"
            )
            village_coords = row.xpath("td")[-2].text
            x, y = village_coords.split("|")
            continent = f"k{y[0]}{x[0]}"
            if continent not in villages:
                villages[continent] = []
            villages[continent].append(
                {"village_url": village_url, "village_coords": village_coords}
            )

        settings["temp"]["villages"] = villages
        settings["temp"]["villages_update_time"] = time.time()

    # Core loop iterate over all villages
    for continent, village_list in villages.items():
        # Skip continents marked as excluded
        if any(
            con in settings["market"]["market_exclude_villages"]
            for con in (continent, continent.upper())
        ):
            continue

        saved_market_history = False
        for village in village_list:
            village_url, village_coords = village.values()

            if village_coords in settings["market"]["market_exclude_villages"]:
                continue

            send_troops_in_the_middle(driver=driver, settings=settings)

            driver.get(village_url)

            # Skip if market has not been built yet
            if (
                driver.execute_script("return game_data.village.buildings.market")
                == "0"
            ):
                continue

            chat = driver.find_element_by_xpath('//*[@id="chat-wrapper"]')
            driver.execute_script("arguments[0].innerHTML = '';", chat)

            resources_doc = lxml.html.fromstring(
                driver.find_element_by_xpath(
                    '//*[@id="header_info"]/tbody/tr/td[4]/table/tbody/tr[1]/td/table/tbody/tr'
                ).get_attribute("innerHTML")
            )
            resources_name = ("wood", "stone", "iron")
            resources_available = {}
            for resource in resources_name:
                resources_available[resource] = int(
                    resources_doc.get_element_by_id(resource).text
                )

            exchange_doc = lxml.html.fromstring(
                driver.find_element_by_xpath(
                    '//*[@id="premium_exchange_form"]/table/tbody'
                ).get_attribute("innerHTML")
            )
            exchange_resources = {
                resource_name: {
                    "current_resource_rate": 0,
                    "max_exchange_resource_can_receive": 0,
                }
                for resource_name in resources_name
            }
            for resource in resources_name:
                resource_capacity = exchange_doc.get_element_by_id(
                    f"premium_exchange_capacity_{resource}"
                ).text
                resource_stock = exchange_doc.get_element_by_id(
                    f"premium_exchange_stock_{resource}"
                ).text
                exchange_resources[resource]["max_exchange_resource_can_receive"] = int(
                    resource_capacity
                ) - int(resource_stock)
                resource_rate = driver.find_element_by_xpath(
                    f'//*[@id="premium_exchange_rate_{resource}"]/div[1]'
                ).text
                exchange_resources[resource]["current_resource_rate"] = int(
                    resource_rate
                )

            if not saved_market_history:
                market_history_file = open(
                    f'market_history_{settings["server_world"]}.txt', "a"
                )
                market_history_file.write(
                    f'{time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())} '
                )
                market_history_file.writelines(
                    f'{resource_name} {value["current_resource_rate"]} '
                    for resource_name, value in exchange_resources.items()
                )
                market_history_file.write(f"K{continent}")
                market_history_file.write("\n")
                market_history_file.close()
                saved_market_history = True

            if all(
                not exchange_resources[resource_name][
                    "max_exchange_resource_can_receive"
                ]
                for resource_name in exchange_resources
            ):
                break
            if all(
                exchange_resources[resource_name]["current_resource_rate"]
                > int(settings["market"][resource_name]["max_exchange_rate"])
                for resource_name in exchange_resources
            ):
                break

            SUM_EXCHANGE_RATE = sum(
                resource["current_resource_rate"]
                for resource in exchange_resources.values()
            )

            STARTING_TRANSPORT_CAPACITY = int(
                driver.find_element_by_xpath(
                    '//*[@id="market_merchant_max_transport"]'
                ).text
            )
            transport_capacity = STARTING_TRANSPORT_CAPACITY
            if not transport_capacity:
                continue

            exchange_resources = dict(
                sorted(
                    exchange_resources.items(),
                    key=lambda item: item[1]["current_resource_rate"],
                )
            )

            min_exchange_rate = min(
                resource["current_resource_rate"]
                for resource in exchange_resources.values()
            )
            max_exchange_rate = max(
                resource["current_resource_rate"]
                for resource in exchange_resources.values()
            )
            for resource_name in exchange_resources:
                max_resource_to_sell = exchange_resources[resource_name][
                    "max_exchange_resource_can_receive"
                ]
                exchange_rate = exchange_resources[resource_name][
                    "current_resource_rate"
                ]

                if (
                    max_resource_to_sell
                    and transport_capacity >= 1000
                    and transport_capacity > exchange_rate
                ):
                    resource_to_sell = min(
                        (
                            max_resource_to_sell,
                            transport_capacity,
                            resources_available[resource_name],
                        )
                    )

                    current_exchange_rate = int(
                        driver.find_element_by_xpath(
                            f'//*[@id="premium_exchange_rate_{resource_name}"]/div[1]'
                        ).text
                    )
                    if (
                        current_exchange_rate
                        > int(
                            settings["market"][resource_name]["max_exchange_rate"]
                        )  # Pomiń jeśli kurs jest powyżej ustalonej wartości
                        or current_exchange_rate >= resources_available[resource_name]
                    ):  # Pomiń jeśli kurs jest wyższy od dostępnych surowców
                        continue

                    if exchange_rate == min_exchange_rate:
                        if resource_to_sell > round(
                            max_exchange_rate
                            / SUM_EXCHANGE_RATE
                            * STARTING_TRANSPORT_CAPACITY
                        ):
                            resource_to_sell = round(
                                max_exchange_rate
                                / SUM_EXCHANGE_RATE
                                * STARTING_TRANSPORT_CAPACITY
                            )
                    elif exchange_rate == max_exchange_rate:
                        if resource_to_sell > round(
                            min_exchange_rate
                            / SUM_EXCHANGE_RATE
                            * STARTING_TRANSPORT_CAPACITY
                        ):
                            resource_to_sell = round(
                                min_exchange_rate
                                / SUM_EXCHANGE_RATE
                                * STARTING_TRANSPORT_CAPACITY
                            )
                    else:
                        if resource_to_sell > round(
                            exchange_rate
                            / SUM_EXCHANGE_RATE
                            * STARTING_TRANSPORT_CAPACITY
                        ):
                            resource_to_sell = round(
                                exchange_rate
                                / SUM_EXCHANGE_RATE
                                * STARTING_TRANSPORT_CAPACITY
                            )
                    resource_to_sell -= current_exchange_rate
                    if resource_to_sell < 1:
                        resource_to_sell = 1

                    input = driver.find_element_by_xpath(
                        f'//*[@id="premium_exchange_sell_{resource_name}"]/div[1]/input'
                    )
                    input.send_keys(f"{resource_to_sell}")
                    input.send_keys(Keys.ENTER)

                    try:  # //*[@id="confirmation-msg"]/div/table/tbody/tr[2]/td[2]
                        final_resource_amount_to_sell = WebDriverWait(
                            driver, 3, 0.025
                        ).until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    f'//*[@id="confirmation-msg"]/div/table/tbody/tr[2]/td[2]',
                                )
                            )
                        )
                    except TimeoutException:
                        driver.find_element_by_xpath(
                            '//*[@id="premium_exchange_form"]/input'
                        ).click()
                        final_resource_amount_to_sell = WebDriverWait(
                            driver, 3, 0.025
                        ).until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    f'//*[@id="confirmation-msg"]/div/table/tbody/tr[2]/td[2]',
                                )
                            )
                        )
                    except StaleElementReferenceException:
                        final_resource_amount_to_sell = WebDriverWait(
                            driver, 3, 0.025
                        ).until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    f'//*[@id="confirmation-msg"]/div/table/tbody/tr[2]/td[2]',
                                )
                            )
                        )
                    final_resource_amount_to_sell = final_resource_amount_to_sell.text
                    final_resource_amount_to_sell = int(
                        re.search(r"\d+", final_resource_amount_to_sell).group()
                    )

                    if (
                        resource_to_sell == 1
                        and final_resource_amount_to_sell > transport_capacity
                        and final_resource_amount_to_sell
                        > resources_available[resource_name]
                    ):
                        driver.find_element(
                            By.CLASS_NAME, "btn.evt-cancel-btn.btn-confirm-no"
                        ).click()
                        input.clear()
                        continue

                    if (
                        final_resource_amount_to_sell
                        > resources_available[resource_name]
                    ):
                        current_exchange_rate = driver.find_element_by_xpath(
                            '//*[@id="confirmation-msg"]/div/p[2]'
                        ).text
                        current_exchange_rate = ceil(
                            final_resource_amount_to_sell
                            / int(re.search(r"\d+", current_exchange_rate).group())
                        )

                        driver.find_element(
                            By.CLASS_NAME, "btn.evt-cancel-btn.btn-confirm-no"
                        ).click()  # Click cancel button

                        final_resource_amount_to_sell = (
                            resources_available[resource_name] - current_exchange_rate
                        )
                        if final_resource_amount_to_sell < 1:
                            final_resource_amount_to_sell = 1
                        input.clear()
                        input.send_keys(  # Correct resources amount
                            f"{final_resource_amount_to_sell}"
                        )
                        input.send_keys(Keys.ENTER)

                    try:
                        WebDriverWait(driver, 3, 0.025).until(
                            EC.element_to_be_clickable(
                                (
                                    By.CLASS_NAME,
                                    f"btn.evt-confirm-btn.btn-confirm-yes",
                                )
                            )
                        ).click()
                    except StaleElementReferenceException:
                        WebDriverWait(driver, 3, 0.025).until(
                            EC.element_to_be_clickable(
                                (
                                    By.CLASS_NAME,
                                    f"btn.evt-confirm-btn.btn-confirm-yes",
                                )
                            )
                        ).click()

                    for _ in range(5):
                        send_troops_in_the_middle(driver=driver, settings=settings)
                        time.sleep(1)

                    transport_capacity = int(
                        driver.find_element(By.ID, "market_merchant_max_transport").text
                    )


def send_back_support(driver: webdriver.Chrome) -> None:
    """Odsyłanie wybranego wsparcia z przeglądanej wioski"""

    code = driver.find_element_by_xpath(
        '//*[@id="withdraw_selected_units_village_info"]/table/tbody'
    ).get_attribute("innerHTML")
    temp = code.split("<tr>")[2:-1]
    omit = 2
    for index in range(len(temp)):
        temp[index] = temp[index].split("<td style")[1:-5]
        if temp[index][0].find("has-input") == -1:
            continue
        del temp[index][4], temp[index][2]
        for row, value in zip(range(len(temp[index])), (2, 3, 5, 7)):
            temp[index][row] = [value, temp[index][row]]
        for row in range(len(temp[index])):
            if temp[index][row][0] == omit:
                continue
            if temp[index][row][1].find("hidden") != -1:
                continue
            ele = driver.find_element_by_xpath(
                f'//*[@id="withdraw_selected_units_village_info"]/table/tbody/tr[{index+2}]/td[{temp[index][row][0]}]'
            )
            html = temp[index][row][1][temp[index][row][1].find("<") : -5]
            html = html[: html.find("value")] + 'value="" ' + html[html.find("min") :]
            driver.execute_script(f"""arguments[0].innerHTML = '{html}';""", ele)


def send_troops(driver: webdriver.Chrome, settings: dict) -> tuple[int, list]:
    """Send troops at given time.
    It can be attack or help.
    You can also use it for fakes.
    """

    send_time = settings["scheduler"]["ready_schedule"][0]["send_time"]
    list_to_send = []
    for cell_in_list in settings["scheduler"]["ready_schedule"]:
        if cell_in_list["send_time"] > send_time + 8:
            break
        list_to_send.append(cell_in_list)

    if len(list_to_send) > 1:
        origin_tab = driver.current_window_handle
        new_tabs = []

    attacks_list_to_repeat = []
    for index, send_info in enumerate(list_to_send):

        if index > 0:
            previous_tabs = set(driver.window_handles)
            driver.switch_to.new_window("tab")
            driver.get(send_info["url"])
            new_tab = set(driver.window_handles).difference(previous_tabs)
            new_tabs.append(*new_tab)
        else:
            driver.get(send_info["url"])

        match send_info["template_type"]:
            case "send_all":

                def choose_all_units_with_exceptions(troops_dict: dict) -> None:
                    """Choose all units and than unclick all unnecessary"""

                    slowest_troop_speed = troops_dict[send_info["slowest_troop"]]
                    for troop_name, troop_speed in list(troops_dict.items()):
                        if troop_speed > slowest_troop_speed:
                            del troops_dict[troop_name]

                    driver.find_element(By.ID, "selectAllUnits").click()
                    doc = lxml.html.fromstring(
                        driver.find_element(
                            By.XPATH, '//*[@id="command-data-form"]/table/tbody/tr'
                        ).get_attribute("innerHTML")
                    )
                    for col in doc:
                        col = col.xpath("table/tbody/tr/td")
                        for troop in col:
                            if troop.get("class") == "nowrap unit-input-faded":
                                continue
                            troop_name = troop.xpath("a")[1].get("data-unit")
                            if troop_name not in troops_dict:
                                troop_button_id = troop.xpath("a")[1].get("id")
                                driver.find_element(By.ID, troop_button_id).click()

                troops_off = {
                    "axe": 18,
                    "light": 10,
                    "marcher": 10,
                    "ram": 30,
                    "catapult": 30,
                    "knight": 10,
                    "snob": 35,
                }

                troops_deff = {
                    "spear": 18,
                    "sword": 22,
                    "archer": 18,
                    "spy": 9,
                    "heavy": 11,
                    "catapult": 30,
                    "knight": 10,
                    "snob": 35,
                }

                if (
                    send_info["send_snob"] == "send_snob"
                    and int(send_info["snob_amount"]) > 1
                ):

                    match send_info["army_type"]:

                        case "only_off":
                            all_troops = troops_off.keys()

                        case "only_deff":
                            all_troops = troops_deff.keys()

                        case _:
                            all_troops = (
                                "spear",
                                "sword",
                                "axe",
                                "archer",
                                "spy",
                                "light",
                                "marcher",
                                "heavy",
                                "ram",
                                "catapult",
                                "knight",
                                "snob",
                            )

                    for troop in all_troops:
                        if int(settings["world_config"]["archer"]) == 0:
                            if troop in ("archer", "marcher"):
                                continue
                        if troop == "snob":
                            continue
                        input_field = driver.find_element(By.ID, f"unit_input_{troop}")
                        troop_number = int(input_field.get_attribute("data-all-count"))
                        if troop_number == 0:
                            continue
                        match troop:
                            case "ram" | "catapult" | "knight":
                                pass
                            case _:
                                troop_number = round(
                                    troop_number
                                    / 100
                                    * int(send_info["first_snob_army_size"])
                                )
                        input_field.send_keys(troop_number)

                else:
                    # Choose all troops to send with exceptions
                    match send_info["army_type"]:

                        case "only_off":

                            choose_all_units_with_exceptions(troops_dict=troops_off)

                        case "only_deff":

                            choose_all_units_with_exceptions(troops_dict=troops_deff)

                if send_info["send_snob"] == "send_snob":
                    if send_info["snob_amount"] and send_info["snob_amount"] != "0":
                        snob_input = driver.find_element(By.ID, "unit_input_snob")
                        snob_input.clear()
                        snob_input.send_keys("1")
                        send_info["snob_amount"] = int(send_info["snob_amount"]) - 1

            case "send_fake":
                # Choose troops to send
                java_script = f'return Math.floor(window.game_data.village.points*{settings["world_config"]["fake_limit"]}/100)'
                min_population = driver.execute_script(java_script)
                current_population = 0
                for troop_name, template_data in send_info["fake_template"].items():
                    troop_input = driver.find_element(By.ID, f"unit_input_{troop_name}")
                    available_troop_number = int(
                        troop_input.get_attribute("data-all-count")
                    )
                    if available_troop_number >= int(
                        template_data["min_value"]
                    ) and available_troop_number <= int(template_data["max_value"]):
                        if (
                            available_troop_number * template_data["population"]
                            >= min_population - current_population
                        ):
                            troop_number = ceil(
                                (min_population - current_population)
                                / template_data["population"]
                            )
                            current_population = min_population
                        else:
                            troop_number = available_troop_number
                            current_population += (
                                available_troop_number * template_data["population"]
                            )
                    elif available_troop_number >= int(template_data["max_value"]):
                        if (
                            int(template_data["max_value"])
                            * template_data["population"]
                            >= min_population - current_population
                        ):
                            troop_number = ceil(
                                (min_population - current_population)
                                / template_data["population"]
                            )
                            current_population = min_population
                        else:
                            troop_number = int(template_data["max_value"])
                            current_population += (
                                int(template_data["max_value"])
                                * template_data["population"]
                            )
                    else:
                        return len(list_to_send), attacks_list_to_repeat
                    troop_input.send_keys(troop_number)
                    if current_population >= min_population:
                        break
                else:
                    if len(list_to_send) == 1:
                        return 1, attacks_list_to_repeat
                    continue

            case "send_my_template":
                # Choose troops to send
                for troop_name, troop_number in send_info["troops"].items():
                    if troop_number:
                        troop_input = driver.find_element(
                            By.ID, f"unit_input_{troop_name}"
                        )
                        troop_input.send_keys(troop_number)

                if send_info["repeat_attack"] and int(send_info["repeat_attack"]):
                    if send_info["repeat_attack_number"]:
                        repeat_attack_number = int(send_info["repeat_attack_number"])
                        if repeat_attack_number > 0:
                            # Add dict to list of attacks to repeat and in the end add to self.to_do
                            attacks_list_to_repeat.append(
                                {
                                    "func": "send_troops",
                                    "start_time": send_info["send_time"]
                                    + 2 * send_info["travel_time"]
                                    + 1,
                                    "server_world": settings["server_world"],
                                    "settings": settings,
                                }
                            )
                            # Add the same attack to scheduler with changed send_time etc.
                            attack_to_add = send_info.copy()
                            if repeat_attack_number == 1:
                                attack_to_add["repeat_attack"] = 0
                            attack_to_add["repeat_attack_number"] = (
                                repeat_attack_number - 1
                            )
                            attack_to_add["send_time"] += (
                                2 * send_info["travel_time"] + 9
                            )
                            arrival_time_in_sec = (
                                attack_to_add["send_time"] + send_info["travel_time"]
                            )
                            arrival_time = time.localtime(arrival_time_in_sec)
                            attack_to_add["arrival_time"] = time.strftime(
                                f"%d.%m.%Y %H:%M:%S:{round(random.random()*100000):0<6}",
                                arrival_time,
                            )
                            settings["scheduler"]["ready_schedule"].append(
                                attack_to_add
                            )

        # Click command_type button (attack or support)
        driver.execute_script(
            f'document.getElementById("{send_info["command"]}").click();'
        )

        # Add snoob
        if send_info["template_type"] == "send_all":
            if "snob_amount" in send_info:
                try:
                    add_snoob = driver.find_element(By.ID, "troop_confirm_train")
                except:
                    if len(list_to_send) > 1:
                        continue
                    return 1, attacks_list_to_repeat
                for _ in range(send_info["snob_amount"]):
                    driver.execute_script("arguments[0].click()", add_snoob)

    if len(list_to_send) > 1:
        driver.switch_to.window(origin_tab)

    for index, send_info in enumerate(list_to_send):
        if index > 0:
            driver.switch_to.window(new_tabs[index - 1])
        current_time = driver.find_elements(By.XPATH, '//*[@id="date_arrival"]/span')
        # Skip to next if didn't find element with id="date_arrival"
        if not current_time:
            continue
        current_time = current_time[0]
        send_button = driver.find_element(By.ID, "troop_confirm_submit")
        arrival_time = re.search(
            r"\d{2}:\d{2}:\d{2}", send_info["arrival_time"]
        ).group()

        if current_time.text[-8:] < arrival_time:
            ms = int(send_info["arrival_time"][-3:])
            if ms <= 10:
                sec = 0
            else:
                sec = (ms + 10) / 1000
            while True:
                current_arrival_time = current_time.text[-8:]
                if current_arrival_time == arrival_time:
                    if sec:
                        time.sleep(sec)
                    driver.execute_script("arguments[0].click()", send_button)
                    break
                elif current_arrival_time > arrival_time:
                    driver.execute_script("arguments[0].click()", send_button)
                    break
        else:
            driver.execute_script("arguments[0].click()", send_button)

    if len(list_to_send) > 1:
        time.sleep(0.5)
        for new_tab in new_tabs:
            driver.switch_to.window(new_tab)
            driver.close()
        driver.switch_to.window(origin_tab)

    return len(list_to_send), attacks_list_to_repeat


def send_troops_in_the_middle(driver: webdriver.Chrome, settings: dict) -> None:
    """The same as send_troops but it is used during the other func run"""

    to_do: list = settings["temp"]["to_do"]

    # Check if should send some troops
    current_time = time.time()
    for task in to_do[1:]:
        if task["start_time"] - 1 > current_time:
            return
        if task["func"] != "send_troops":
            continue
        settings = task["settings"]
        break
    else:
        return

    # Save current tab, open new and switch to it
    origin_tab = driver.current_window_handle
    driver.switch_to.new_window("tab")

    try:
        (send_number_times, attacks_to_repeat) = send_troops(
            driver=driver, settings=settings
        )
    except BaseException:
        unwanted_page_content(driver=driver, settings=settings)
        try:
            (send_number_times, attacks_to_repeat) = send_troops(
                driver=driver, settings=settings
            )
        except BaseException:
            send_number_times = 1
            attacks_to_repeat = []
    finally:
        # Close current tab and switch to original one
        driver.close()
        driver.switch_to.window(origin_tab)

    # Clean from settings and to_do
    del settings["scheduler"]["ready_schedule"][0:send_number_times]

    index_to_del = []
    for index, row_data in enumerate(to_do):
        if row_data["func"] != "send_troops":
            continue
        if row_data["server_world"] != settings["server_world"]:
            continue
        index_to_del.append(index)
        if len(index_to_del) == send_number_times:
            break
    for index in sorted(index_to_del, reverse=True):
        del to_do[index]

    # Sort all added attacks in scheduler and add them in to_do
    if attacks_to_repeat:
        settings["scheduler"]["ready_schedule"].sort(key=lambda x: x["send_time"])
        for attack in attacks_to_repeat:
            to_do.append(attack)
        to_do.sort(key=lambda sort_by: sort_by["start_time"])


def train_knight(driver: webdriver.Chrome) -> None:
    """Train knights to gain experience and lvl up"""


def unwanted_page_content(
    driver: webdriver.Chrome, settings: dict[str], html: str = ""
) -> bool:
    """Deal with: chat disconnected, session expired,
    popup boxes like: daily bonus, tribe quests,
    captcha etc.
    """

    try:
        if not html:
            html = driver.page_source

        # If disconected/sesion expired
        if (
            html.find("chat-disconnected") != -1
            or "session_expired" in driver.current_url
        ):
            return log_in(driver, settings)

        # If captcha on page
        if html.find("captcha") != -1:
            captcha_check(driver=driver, settings=settings, page_source=html)
            return True

        # Bonus dzienny i pozostałe okna należacę do popup_box_container
        elif html.find("popup_box_container") != -1:
            # Poczekaj do 2 sekund w celu wczytania całości dynamicznego kontentu
            for _ in range(25):
                time.sleep(0.1)
                html = driver.page_source
                if html.find("popup_box_daily_bonus") != -1:
                    break

            # Odbierz bonus dzienny
            if html.find("popup_box_daily_bonus") != -1:

                def open_daily_bonus() -> bool:
                    try:
                        popup_box_html = (
                            WebDriverWait(driver, 5, 0.1)
                            .until(
                                EC.element_to_be_clickable(
                                    (By.ID, "popup_box_daily_bonus")
                                )
                            )
                            .get_attribute("innerHTML")
                        )
                        WebDriverWait(driver, 2, 0.1).until(
                            EC.element_to_be_clickable(
                                (By.CLASS_NAME, "popup_box_close.tooltip-delayed")
                            )
                        )
                        bonuses = driver.find_elements(
                            By.XPATH,
                            '//*[@id="daily_bonus_content"]/div/div/div/div/div[@class="db-chest unlocked"]/../div[3]/a',
                        )
                        for bonus in bonuses:
                            driver.execute_script(
                                "return arguments[0].scrollIntoView(true);", bonus
                            )
                            bonus.click()

                        if popup_box_html.find("icon header premium") != -1:
                            WebDriverWait(driver, 2, 0.25).until(
                                EC.element_to_be_clickable(
                                    (By.CLASS_NAME, "popup_box_close.tooltip-delayed")
                                )
                            ).click()

                        # Check if popup_box_daily_bonus was closed
                        try:
                            if WebDriverWait(driver, 3, 0.05).until(
                                EC.invisibility_of_element_located(
                                    (By.ID, "popup_box_daily_bonus")
                                )
                            ):
                                return True
                        except:
                            WebDriverWait(driver, 3, 0.05).until(
                                EC.element_to_be_clickable(
                                    (By.CLASS_NAME, "popup_box_close.tooltip-delayed")
                                )
                            ).click()
                            if WebDriverWait(driver, 3, 0.05).until(
                                EC.invisibility_of_element_located(
                                    (By.ID, "popup_box_daily_bonus")
                                )
                            ):
                                return True

                        return False

                    except BaseException:
                        return False

                # Próbuję odebrać bonus dzienny jeśli się nie uda odświeża stronę i próbuję ponownie.
                # W razie niepowodzenia tworzy log błędu
                if open_daily_bonus():
                    return True

                driver.refresh()
                if open_daily_bonus():
                    return True

                log_error(
                    driver=driver, msg="unwanted_page_content -> open_daily_bonus"
                )
                return False

            # Zamknij wszystkie popup_boxy które nie dotyczą bonusu dziennego
            else:
                driver.find_element(
                    By.CLASS_NAME, "popup_box_close.tooltip-delayed"
                ).click()
                try:
                    WebDriverWait(driver, 3, 0.05).until(
                        EC.invisibility_of_element_located(
                            (By.CLASS_NAME, "popup_box_container")
                        )
                    )
                except:
                    return False
                return True

        # Zamyka otwarte okno grup
        elif driver.find_elements_by_xpath(
            '//*[@id="open_groups"][@style="display: none;"]'
        ):
            driver.execute_script("villageDock.close(event);")

            return True

        # Zamyka okno promki premium
        elif driver.find_elements(By.ID, "payment_box_iframe_container"):
            driver.switch_to.frame("pay_frame")
            driver.find_element(By.CLASS_NAME, "Button-close").click()
            driver.switch_to.default_content()

            return True

        # Nieznane -> log_error
        else:
            log_error(driver=driver, msg="unwanted_page_content -> else(uknown error)")
            return False

    except BaseException:
        log_error(
            driver=driver,
            msg="unwanted_page_content -> error while handling common errors",
        )
        return False


def mine_coin(driver: webdriver.Chrome) -> None:

    village_palace_url = (
        "https://pl173.plemiona.pl/game.php?village=46740&screen=snob",
        "https://pl173.plemiona.pl/game.php?village=15449&screen=snob",
    )
    village_market_url = (
        "https://pl173.plemiona.pl/game.php?village=46740&screen=market&order=distance&dir=ASC&target_id=0&mode=call&group=110555&",
        "https://pl173.plemiona.pl/game.php?village=15449&screen=market&order=distance&dir=ASC&target_id=0&mode=call&group=110559&",
    )

    for palace_url, market_url in zip(village_palace_url, village_market_url):
        # Wybij monety -> pałac
        driver.get(palace_url)
        try:
            max_coin = driver.find_element(By.ID, "coin_mint_fill_max")
            driver.execute_script(
                "return arguments[0].scrollIntoView(false);", max_coin
            )
            footer_height = driver.find_element(By.ID, "footer").size["height"]
            driver.execute_script(f"scrollBy(0, {footer_height});")
            max_coin.click()
            driver.find_element(
                By.XPATH,
                '//*[@id="content_value"]/table[2]/tbody/tr/td[2]/table[4]/tbody/tr[10]/td[2]/form/input[2]',
            ).click()
        except:
            pass
        # Wezwij surowce -> rynek
        driver.get(market_url)
        driver.find_element(By.ID, "ds_body").send_keys("4")
        request_resources = driver.find_element(
            By.XPATH,
            '//*[@id="content_value"]/table[2]/tbody/tr/td[2]/form[1]/input[2]',
        )
        driver.execute_script(
            "return arguments[0].scrollIntoView(false);", request_resources
        )
        time.sleep(1.5)
        request_resources.click()
