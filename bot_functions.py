import ast
import logging
import random
import re
import threading
import time
import traceback
import winsound
from math import ceil, sqrt

import lxml.html
import requests
from anticaptchaofficial.hcaptchaproxyless import *
from anycaptcha import AnycaptchaClient, HCaptchaTaskProxyless
from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from ttkbootstrap.toast import ToastNotification
from app_logging import CustomLogFormatter

import email_notifications
from config import ANY_CAPTCHA_API_KEY, SMS_API_TOKEN
from decorators import log_errors
from gui_functions import custom_error

logger = logging.getLogger(__name__)
f_handler = logging.FileHandler("logs/log.txt")
f_format = CustomLogFormatter(
    "%(levelname)s | %(name)s | %(asctime)s %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
)
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
logger.propagate = False


def attacks_labels(driver: webdriver.Chrome, settings: dict[str, str | dict]) -> bool:
    """Etykiety ataków"""

    COUNTRY_CODE: str = settings["country_code"]

    if not int(
        driver.execute_script("return window.game_data.player.incomings")
    ) or not driver.execute_script("return premium"):
        return False

    # Open incoming attacks tab with group id = 0 which points to all villages
    current_village_id = driver.execute_script("return game_data.village.id")
    url = f'https://{settings["server_world"]}.{settings["game_url"]}'
    driver.get(
        f"{url}/game.php?village={current_village_id}&screen=overview_villages&mode=incomings&type=unignored&subtype=attacks&group=0&page=-1"
    )
    captcha_check(driver=driver, settings=settings)
    # Check current label command and ommit changing it if it is already correct
    label_command_value = driver.execute_script(
        """return document.querySelector(
        '#paged_view_content > div.overview_filters > form > table > tbody > tr:nth-child(2) > td:nth-child(2) > input[type=text]'
        ).value;
        """
    )
    translate = {"pl": "Atak", "de": "Angriff"}
    if label_command_value != translate[COUNTRY_CODE]:
        if (  # Check if filter manager is opened if not than open it
            driver.find_element(By.XPATH, '//*[@id="paged_view_content"]/div[2]')
            .get_attribute("style")
            .find("display: none")
            != -1
        ):
            manage_filters = WebDriverWait(driver, 5, 0.1).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="paged_view_content"]/a')
                )
            )
            manage_filters.click()
        # Close chat
        driver.execute_script('document.getElementById("chat-wrapper").innerHTML = "";')
        etkyieta_rozkazu = WebDriverWait(driver, 5, 0.1).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[2]/td[2]/input',
                )
            )
        )
        etkyieta_rozkazu.clear()
        etkyieta_rozkazu.send_keys(translate[COUNTRY_CODE])
        WebDriverWait(driver, 5, 0.1).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[6]/td/input',
                )
            )
        ).click()
        WebDriverWait(driver, 5, 0.1).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a'))
        )

    # Quit if no new attacks
    if not driver.find_elements(By.ID, "incomings_table"):
        return True

    # Close chat
    driver.execute_script('document.getElementById("chat-wrapper").innerHTML = "";')

    select_all = WebDriverWait(driver, 5, 0.1).until(
        EC.element_to_be_clickable((By.ID, "select_all"))
    )
    driver.execute_script("return arguments[0].scrollIntoView(true);", select_all)
    select_all.click()
    WebDriverWait(driver, 5, 0.1).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                '//*[@id="incomings_table"]//input[@type="submit" and @name="label"]',
            )
        )
    ).click()

    # Close chat
    driver.execute_script('document.getElementById("chat-wrapper").innerHTML = "";')

    notifications = settings["notifications"]
    if any(
        (
            notifications["email_notifications"],
            notifications["sms_notifications"],
            notifications["sound_notifications"],
        )
    ):
        if (  # Check if filter manager is opened if not than open it
            driver.find_element(By.XPATH, '//*[@id="paged_view_content"]/div[2]')
            .get_attribute("style")
            .find("display: none")
            != -1
        ):
            manage_filters = WebDriverWait(driver, 5, 0.1).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="paged_view_content"]/a')
                )
            )
            manage_filters.click()

        etkyieta_rozkazu = WebDriverWait(driver, 5, 0.1).until(
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
        WebDriverWait(driver, 5, 0.1).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[6]/td/input',
                )
            )
        ).click()
        WebDriverWait(driver, 5, 0.1).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a'))
        )

        # Return True if no new attacks with snob were found
        if not driver.find_elements(By.ID, "incomings_table"):
            return True

        # Close chat
        driver.execute_script('document.getElementById("chat-wrapper").innerHTML = "";')

        def get_attacks_info() -> str:
            reach_times = [
                reach_time.text
                for reach_time in driver.find_elements(
                    By.XPATH, '//*[@id="incomings_table"]/tbody/tr/td[6]'
                )
            ]
            villages_coords = [  # (?s:.*)
                re.findall(r"\d{3}\|\d{3}", village_coord.text)[-1]
                for village_coord in driver.find_elements(
                    By.XPATH, '//*[@id="incomings_table"]/tbody/tr/td[2]'
                )
            ]
            attacks_by_village = {}
            for village_coords, attack_time in zip(villages_coords, reach_times):
                if village_coords not in attacks_by_village:
                    attacks_by_village[village_coords] = [attack_time]
                    continue
                attacks_by_village[village_coords].append(attack_time)

            # Sort dict by first value in each key
            attacks_by_village = dict(
                sorted(attacks_by_village.items(), key=lambda item: item[1][0])
            )

            message = "\n".join(
                f"\n{coords}\n" + "\n".join(attacks)
                for coords, attacks in attacks_by_village.items()
            )
            return message

        if notifications["email_notifications"]:
            total_attacks_number = driver.find_element(
                By.XPATH, '//*[@id="incomings_table"]/tbody/tr[1]/th[1]'
            ).text
            total_attacks_number = re.search(r"\d+", total_attacks_number).group()
            attacks_info = get_attacks_info()

            threading.Thread(
                target=email_notifications.send_email,
                kwargs={
                    "email_recepients": settings["notifications"]["email_address"],
                    "email_subject": f"Wykryto grubasy {settings['world_in_title']}",
                    "email_body": f'Wykryto grubasy o godzinie {time.strftime("%H:%M:%S %d.%m.%Y", time.localtime())}\n\n'
                    f"Liczba nadchodzących grubasów: {total_attacks_number}\n"
                    f"{attacks_info}",
                },
            ).start()

        if notifications["sms_notifications"]:
            url = "https://sms-api.ddns.net/send_sms"
            headers = {
                "Content-Type": "application/json",
                "Authorization": SMS_API_TOKEN,
            }
            if "attacks_info" not in locals():
                attacks_info = get_attacks_info()
            data = {
                "number": notifications["phone_number"],
                "text": f"Wykryto grubasy {settings['world_in_title']}\n{attacks_info}",
            }
            threading.Thread(
                target=requests.post,
                kwargs={"url": url, "json": data, "headers": headers},
            ).start()

        if notifications["sound_notifications"]:
            winsound.PlaySound(
                "sounds//alarm.wav", winsound.SND_ASYNC + winsound.SND_LOOP
            )
            toast = ToastNotification(
                title="TribalWarsBot Alert!",
                message="Wykryto nadchodzące grubasy. Kliknij w komunikat w celu wyłączenia alertu.",
                topmost=True,
                bootstyle="danger",
            )
            toast.show_toast()
            toast.toplevel.bind(
                "<Destroy>", lambda args: winsound.PlaySound(None, winsound.SND_PURGE)
            )

        # Describe attacks
        for label in driver.find_elements(
            By.XPATH, '//*[@id="incomings_table"]/tbody/tr/td[1]/span/span/a[2]'
        ):
            driver.execute_script(
                'return arguments[0].scrollIntoView({block: "center"});', label
            )
            label.click()

        current_time = time.strftime("%H:%M:%S %d.%m.%Y", time.localtime())
        for label_input in driver.find_elements(
            By.XPATH, '//*[@id="incomings_table"]/tbody/tr/td[1]/span/span[2]/input[1]'
        ):
            label_input.clear()
            label_input.send_keys(f"szlachta notified {current_time}")
            label_input.send_keys(Keys.ENTER)

    return True


def auto_farm(driver: webdriver.Chrome, settings: dict[str, str | dict]) -> None:
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
        driver.execute_script("if (!villageDock.docked) {villageDock.open(event);}")
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
            select = Select(driver.find_element(By.ID, "group_id"))
            select.select_by_visible_text(settings["farm_group"])
            time.sleep(0.2)
            try:
                WebDriverWait(driver, 5, 0.033).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//*[@id="group_table"]/tbody/tr[1]/td[1]/a')
                    )
                ).click()
            except StaleElementReferenceException:
                WebDriverWait(driver, 5, 0.033).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//*[@id="group_table"]/tbody/tr[1]/td[1]/a')
                    )
                ).click()
        driver.execute_script("if (villageDock.docked) {villageDock.close(event);}")
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
    troops_speed = {
        "spear": 18,
        "sword": 22,
        "axe": 18,
        "archer": 18,
        "spy": 9,
        "light": 10,
        "marcher": 10,
        "heavy": 11,
        "ram": 30,
        "catapult": 30,
        "knight": 10,
        "snob": 35,
    }

    if "farm_village_to_skip" not in settings["temp"]:
        settings["temp"]["farm_village_to_skip"] = {}

    # Główna pętla funkcji
    while True:

        # Ukrywa chat
        driver.execute_script('document.getElementById("chat-wrapper").innerHTML = "";')

        # Szablon A i B nazwy jednostek i ich liczebność
        doc = lxml.html.fromstring(
            driver.find_element(By.ID, "content_value").get_attribute("innerHTML")
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
        troops_home = doc.xpath('//*[@id="units_home"]/tbody/tr[2]')[0]
        available_troops = {
            troop_name: int(troops_home.xpath(f'td[@id="{troop_name}"]')[0].text)
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

        # Lista przycisków do wysyłki szablonów A, B i C
        villages_to_farm = {}

        if settings["A"]["active"]:
            villages_to_farm["A"] = 9  # Szablon A
        if settings["B"]["active"]:
            villages_to_farm["B"] = 10  # Szablon B
        if settings["C"]["active"]:
            villages_to_farm["C"] = 11  # Szablon C
            skip["C"] = False
            template_troops["C"] = {}

        # Wysyłka wojsk w asystencie farmera
        start_time = 0
        no_units = False
        for index, template in enumerate(villages_to_farm):
            if skip[template]:
                continue

            captcha_solved = False
            if captcha_check(driver=driver, settings=settings):
                captcha_solved = True

            max_attacks_number = settings[template]["attacks_number"]
            villages_to_farm[template] = driver.find_elements(
                By.XPATH,
                f'//*[@id="plunder_list"]/tbody/tr/td[{villages_to_farm[template]}]/a',
            )

            farm = lxml.html.fromstring(
                driver.find_element(
                    By.CSS_SELECTOR, "#plunder_list tbody"
                ).get_attribute("innerHTML")
            )
            walls = tuple(
                "?" if "?" in wall.xpath("text()") else int(wall.xpath("text()")[0])
                for wall in farm.xpath("tr/td[7]")
            )

            def get_report_id(index: int) -> str:
                report_id = farm.xpath(f"tr[{index+3}]/td[4]/a/@href")[0]
                report_id = re.search(r"view=(\d+)", report_id).group(1)
                return report_id

            def skip_village(index: int) -> bool:
                village_id = farm.xpath(f"tr[{index+3}]/@id")[0]
                report_id = get_report_id(index)
                if (
                    village_id in settings["temp"]["farm_village_to_skip"]
                    and report_id
                    in settings["temp"]["farm_village_to_skip"][village_id]
                ):
                    return True
                return False

            # Loot farm rule
            loot = []
            if settings[template]["farm_rules"]["loot"] != "mix_loot":

                def get_page(url: str) -> str:
                    return driver.execute_script(
                        f"""
                        const xhr = new XMLHttpRequest();
                        ready_status = 0;
                        xhr.onload = () => {{
                            page_source = xhr.responseXML;
                            ready_status = 1;
                        }}
                        xhr.open("GET", "{url}");
                        xhr.responseType = "document";
                        xhr.send();        
                        """
                    )

                if "A" in template:
                    troops_capacity = int(
                        "".join(
                            doc.xpath(
                                "div[2]/div/form/table/tbody/tr[2]/td[last()]/text()"
                            )
                        )
                    )
                if "B" in template:
                    troops_capacity = int(
                        "".join(
                            doc.xpath(
                                "div[2]/div/form/table/tbody/tr[4]/td[last()]/text()"
                            )
                        )
                    )
                if "C" in template:  # Choose bigger from A and B
                    troops_capacity = max(
                        int(
                            "".join(
                                doc.xpath(
                                    "div[2]/div/form/table/tbody/tr[2]/td[last()]/text()"
                                )
                            )
                        ),
                        int(
                            "".join(
                                doc.xpath(
                                    "div[2]/div/form/table/tbody/tr[4]/td[last()]/text()"
                                )
                            )
                        ),
                    )
                # Append True to loot if previous full loot or False if not full
                for index, row in enumerate(farm.xpath("tr/td[3]")):
                    if row.xpath("img[@src]"):
                        if row.xpath("img/@src")[0].endswith("1.png"):
                            loot.append(True)
                            continue
                    # Append True if there are more resource than troop can hanle
                    else:
                        if skip_village(index=index):
                            print("skip")
                            print(settings["temp"]["farm_village_to_skip"])
                            loot.append(False)
                            continue

                        get_page(farm.xpath(f"tr[{index+3}]/td[4]/a/@href")[0])
                        while not driver.execute_script("return ready_status"):
                            time.sleep(0.01)
                        report = driver.execute_script(
                            "return page_source.getElementById('attack_info_def_units').innerHTML"
                        )
                        report = lxml.html.fromstring(report)
                        if sum(
                            int(troop)
                            for troop in report.xpath(
                                "//tbody/tr[last()-1]/td[@class]/text()"
                            )
                        ):
                            # If not empty skip it and add to settings['temp']
                            village_id = farm.xpath(f"tr[{index+3}]/@id")[0]
                            settings["temp"]["farm_village_to_skip"][
                                village_id
                            ] = get_report_id(index=index)
                            loot.append(False)
                            continue
                        resource = sum(
                            int("".join(res.xpath("text()")))
                            for res in farm.xpath(
                                f'tr[{index+3}]/td[6]/span/span[@class="res"]'
                            )
                        )
                        if resource > troops_capacity:
                            loot.append(True)
                            continue
                    loot.append(False)

            if "C" in template:
                units_home = driver.find_element(
                    By.CSS_SELECTOR, "#units_home tbody"
                ).get_attribute("innerHTML")
                units_home = lxml.html.fromstring(units_home)
                units_amount = units_home.xpath("tr[2]/td")
                for unit_amount in units_amount[1:]:
                    if not int(unit_amount.text_content()):
                        continue
                    template_troops[template][unit_amount.xpath("@id")[0]] = int(
                        unit_amount.text_content()
                    )

            # Travel time rule
            max_distance = 0.0
            if settings[template]["farm_rules"]["max_travel_time"]:
                distance = tuple(
                    float(row.xpath("text()")[0]) for row in farm.xpath("tr/td[8]")
                )
                army_speed = max(
                    troops_speed[unit] for unit in template_troops[template]
                )
                max_distance: float = (
                    settings[template]["farm_rules"]["max_travel_time"] / army_speed
                )

            for village_number, (village, wall) in enumerate(
                zip(villages_to_farm[template], walls)
            ):
                # Attacks number requirements
                if (
                    not settings[template]["max_attacks"]
                    and village_number >= max_attacks_number
                ):
                    break

                # Skip villages which has some troops in
                if skip_village(village_number):
                    print("skip2")
                    print(settings["temp"]["farm_village_to_skip"])
                    continue
                # Loot requirements
                if loot:
                    # For max_loot
                    if settings[template]["farm_rules"]["loot"] == "max_loot":
                        if village_number >= len(loot):
                            logger.warning(
                                msg=f"\nvillage_number {village_number} loot = {len(loot)}\n"
                                f"villages_to_farm = {len(villages_to_farm[template])} walls = {len(walls)}"
                            )
                            break
                        if not loot[village_number]:
                            continue
                    # For min_loot
                    else:
                        if village_number >= len(loot):
                            logger.warning(
                                msg=f"\nvillage_number {village_number} loot = {len(loot)}\n"
                                f"villages_to_farm = {len(villages_to_farm[template])} walls = {len(walls)}"
                            )
                            break
                        if loot[village_number]:
                            continue
                # Travel time requirements
                if max_distance and distance[village_number] > max_distance:
                    break
                # Walls requirements
                if isinstance(wall, str) and not settings[template]["wall_ignore"]:
                    continue
                if (
                    settings[template]["wall_ignore"]
                    or settings[template]["min_wall"]
                    <= wall
                    <= settings[template]["max_wall"]
                ):
                    # Troops number for template A and B
                    if template in ("A", "B"):
                        for unit, number in template_troops[template].items():
                            if available_troops[unit] - number < 0:
                                no_units = True
                                break
                            available_troops[unit] -= number
                        if no_units:
                            break
                    # Template C
                    else:
                        if any(
                            True if number < 0 else False
                            for number in template_troops[template].values()
                        ):
                            no_units = True
                            break
                        troops_to_send = ast.literal_eval(
                            village.get_attribute("data-units-forecast")
                        )
                        for unit, number in troops_to_send.items():
                            if not number:
                                continue
                            template_troops[template][unit] -= int(number)

                        units_home = driver.find_element(
                            By.CSS_SELECTOR, "#units_home tbody"
                        ).get_attribute("innerHTML")
                        units_home = lxml.html.fromstring(units_home)
                        units_checkboxes = units_home.xpath("tr[1]/th")
                        units_amount = units_home.xpath("tr[2]/td")

                        for unit_checkbox, unit_amount in zip(
                            units_checkboxes, units_amount
                        ):

                            if "checked" in unit_checkbox.xpath("input/@checked"):
                                if int(unit_amount.text_content()) > 0:
                                    break
                        else:
                            break

                    if not settings["temp"]["main_window"].running:
                        return

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
                    try:
                        village.click()
                    except StaleElementReferenceException:
                        break

                start_time = time.time()

            # Checks if there is other template to send
            if index < len(villages_to_farm) - 1:
                no_units = False
                driver.refresh()
                driver.execute_script(
                    'document.getElementById("chat-wrapper").innerHTML = "";'
                )

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


@log_errors(re_raise=True)
def captcha_check(driver: webdriver.Chrome, settings: dict[str]) -> bool:
    """Check for captcha existence.

    If exist, wait until solved and than update captcha counter.
    """

    search_for_captcha = 'return document.querySelector(".h-captcha, .captcha")'
    if driver.execute_script(search_for_captcha):

        find_captcha_time = time.time()
        if (
            "last_captcha_solved" in settings["temp"]
            and find_captcha_time - settings["temp"]["last_captcha_solved"] < 60
        ):
            driver.refresh()
            # Return if no captcha were find after page refresh
            if not driver.execute_script(search_for_captcha):
                return True

        logger.info("start solving captcha")

        def simple_solve_captcha(captcha_selector: str) -> bool:
            # Switch to frame when it is available
            WebDriverWait(driver, 3, 0.05).until(
                EC.frame_to_be_available_and_switch_to_it(
                    (By.CSS_SELECTOR, f"{captcha_selector} iframe")
                )
            )
            WebDriverWait(driver, 3, 0.05).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[id=checkbox]"))
            ).click()
            driver.switch_to.default_content()
            try:
                WebDriverWait(driver, 3, 0.1).until(
                    lambda _: False
                    if driver.execute_script(search_for_captcha)
                    else True
                )
                return True
            except TimeoutException:
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                return False

        def get_token() -> str | bool:

            api_key = ANY_CAPTCHA_API_KEY
            website_url = driver.current_url[: driver.current_url.rfind("/")]
            website_key = re.search(
                r"&sitekey=(.*?)&",
                WebDriverWait(driver, 3, 0.05)
                .until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "iframe[title='widget containing checkbox for hCaptcha security challenge']",
                        )
                    )
                )
                .get_attribute("src"),
            ).group(1)
            client = AnycaptchaClient(api_key)
            task = HCaptchaTaskProxyless(
                website_url=website_url, website_key=website_key
            )
            job = client.createTask(task)
            # Notify user that captcha solving is in process
            iframe_width = driver.execute_script(
                f"return document.querySelector('{captcha_selector} iframe').clientWidth"
            )
            driver.execute_script(
                f"""const captcha_container = document.querySelectorAll("{captcha_selector} *:last-child")[0];
                const div_to_add = "<div id='kspec' style='width: {iframe_width};'>Solving captcha please wait..</div>"
                captcha_container.insertAdjacentHTML("afterend", div_to_add);"""
            )
            job.join()
            result = job.get_solution_response()

            if result.find("ERROR") != -1:
                logger.error(msg=f"task finished with error {result}")
                return False
            else:
                # If everything is fine result contain token
                return result

        def hard_solve_captcha() -> bool:
            token = get_token()
            driver.execute_script("document.querySelector('#kspec').remove();")
            if token:
                driver.execute_script(
                    f"document.getElementById('anycaptchaSolveButton').onclick('{token}');"
                )
                return True
            return False

        get_captcha_selector = """if (document.querySelector('.h-captcha')) {return '.h-captcha'}
            else if (document.querySelector('.captcha')) {return '.captcha'}
            else {return}
            """
        captcha_selector = driver.execute_script(get_captcha_selector)

        try:
            if simple_solve_captcha(captcha_selector):
                logger.info("captcha solved the easy way")
                return True
        except TimeoutException:
            driver.switch_to.default_content()
            logger.error("error when solving the easy way")

        if hard_solve_captcha():
            logger.info("captcha solved the hard way")
            settings["temp"]["captcha_counter"].set(
                settings["temp"]["captcha_counter"].get() + 1
            )
            settings["temp"]["last_captcha_solved"] = find_captcha_time
            return True

        logger.info("error when dealing with captcha")
        driver.refresh()

        return True
    return False


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

    # Open village selector
    driver.execute_script("if (!villageDock.docked) {villageDock.open(event);}")
    groups = (
        WebDriverWait(driver, 10, 0.033)
        .until(EC.presence_of_element_located((By.ID, "group_id")))
        .get_attribute("innerHTML")
    )
    # Close village selector
    driver.execute_script("if (villageDock.docked) {villageDock.close(event);}")
    groups = [group[1:-1] for group in re.findall(r">[^<].+?<", groups)]
    settings["groups"].clear()
    settings["groups"].extend(groups)
    for combobox in args:
        combobox["values"] = settings["groups"]

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
        driver.find_element(By.XPATH, '//*[@id="paged_view_content"]/div[2]')
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
        driver.find_element(
            By.ID, "incomings_table"
        )  # Czy są ataki spełniające powyższe kryteria
    except:
        pass

    targets = driver.find_elements(
        By.XPATH, '//*[@id="incomings_table"]/tbody/tr/td[2]/a'
    )
    dates = driver.find_elements(By.XPATH, '//*[@id="incomings_table"]/tbody/tr/td[6]')

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
            driver.execute_script("if (!villageDock.docked) {villageDock.open(event);}")
            current_group = (
                WebDriverWait(driver, 5, 0.033)
                .until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//*[@id="group_id"]/option[@selected="selected"]')
                    )
                )
                .text
            )

            if current_group != settings["gathering_group"]:
                select = Select(driver.find_element(By.ID, "group_id"))
                select.select_by_visible_text(settings["gathering_group"])
                time.sleep(0.2)
                try:
                    WebDriverWait(driver, 3, 0.025).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, '//*[@id="group_table"]/tbody/tr[1]/td[1]/a')
                        )
                    ).click()
                except StaleElementReferenceException:
                    WebDriverWait(driver, 3, 0.025).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, '//*[@id="group_table"]/tbody/tr[1]/td[1]/a')
                        )
                    ).click()
            driver.execute_script("if (villageDock.docked) {villageDock.close(event);}")
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

    # Core całej funkcji, kończy gdy przejdzie przez wszystkie wioski
    while True:

        if not settings["temp"]["main_window"].running:
            return []

        send_troops_in_the_middle(driver=driver, settings=settings)
        captcha_check(driver=driver, settings=settings)

        page_source = driver.page_source

        # Skip to next village if current one doesn't have place
        place_str = re.search(r'"place":"\d"', page_source).group()
        if re.search(r"\d", place_str).group() == "0":
            driver.find_element(By.ID, "ds_body").send_keys("d")
            current_village_id = driver.execute_script(
                "return window.game_data.village.id;"
            )
            if starting_village == current_village_id:
                if "url_to_gathering" not in kwargs:
                    return list_of_dicts
                else:
                    return []
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
                settings["gathering_troops"][troop_name]["use"]
                and int(troop_number[1:-1]) > 0
            ):
                available_troops[troop_name] = (
                    int(troop_number[1:-1])
                    - settings["gathering_troops"][troop_name]["left_in_village"]
                )
                if (
                    available_troops[troop_name]
                    > settings["gathering_troops"][troop_name]["send_max"]
                ):
                    available_troops[troop_name] = settings["gathering_troops"][
                        troop_name
                    ]["send_max"]

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
                    settings["gathering"]["ommit"][ele]
                    for ele in settings["gathering"]["ommit"]
                ),
            )
        ):
            if row[0].get("class") != "inactive-view" or row[1]:
                del troops_to_send[number + 1]

        # Ukrywa chat
        driver.execute_script('document.getElementById("chat-wrapper").innerHTML = "";')

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
        max_resources = settings["gathering_max_resources"]
        round_ups_per_troop = {troop_name: 0 for troop_name in available_troops}
        for key in troops_to_send:
            if not settings["temp"]["main_window"].running:
                return []
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
                if not troops_to_send[key][troop_name] > 0:
                    continue
                if reduce_ratio != 1:
                    driver.execute_script(
                        f"""
                        let field = $(`[name='{troop_name}']`);
                        field.trigger('keydown');
                        field.val('{round(troops_to_send[key][troop_name] * reduce_ratio)}');
                        field.trigger('keyup');
                    """
                    )
                else:
                    driver.execute_script(
                        f"""
                        let field = $(`[name='{troop_name}']`);
                        field.trigger('keydown');
                        field.val('{troops_to_send[key][troop_name]}');
                        field.trigger('keyup');
                    """
                    )
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
            driver.execute_script("arguments[0].click()", start)
            WebDriverWait(driver, 3, 0.01).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        f'//*[@id="scavenge_screen"]/div/div[2]/div[{key}]/div[3]/div/ul/li[4]/span[@class="return-countdown"]',
                    )
                )
            )

        if "url_to_gathering" in kwargs:

            # Zwraca docelowy url i czas zakończenia zbieractwa w danej wiosce
            doc = lxml.html.fromstring(
                driver.find_element(
                    By.XPATH, '//*[@id="scavenge_screen"]/div/div[2]'
                ).get_attribute("innerHTML")
            )
            doc = doc.xpath("//div/div[3]/div/ul/li[4]/span[2]")
            if troops_to_send and not [ele.text for ele in doc]:
                for _ in range(10):
                    time.sleep(0.2)
                    doc = lxml.html.fromstring(
                        driver.find_element(
                            By.XPATH, '//*[@id="scavenge_screen"]/div/div[2]'
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
            driver.find_element(By.ID, "ds_body").send_keys("d")
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
        driver.find_element(By.ID, "ds_body").send_keys("d")
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

    logger.error(f"{msg}\n" f"{driver.current_url}\n")
    driver.save_screenshot(
        f'logs/{time.strftime("%d.%m.%Y %H_%M_%S", time.localtime())}.png'
    )


def log_in(driver: webdriver.Chrome, settings: dict) -> bool:
    """Logowanie"""

    try:
        try:
            driver.get(
                f"https://www.{settings['game_url']}/page/play/{settings['server_world']}"
            )
            logger.info("123")
            logger.info("234")
            log_error(driver, "bleble")
            log_error(driver, "bleble2")
        except WebDriverException as e:
            if "cannot determine loading status" in e.msg:
                pass

        # Czy prawidłowo wczytano i zalogowano się na stronie
        if f"{settings['server_world']}.{settings['game_url']}" in driver.current_url:
            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            return True

        # Ręczne logowanie na stronie plemion
        elif f"https://www.{settings['game_url']}/" == driver.current_url:

            if not "game_user_name" in settings:
                if not driver.find_elements(By.ID, "login_form"):
                    return log_in(driver=driver, settings=settings)
                driver.switch_to.window(driver.current_window_handle)
                custom_error(
                    message="Zaloguj się na otwartej stronie plemion.\n"
                    "Pole zapamiętaj mnie powinno być zaznaczone."
                )
                if WebDriverWait(driver, 60, 0.25).until(
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
        for village_resources in driver.find_elements(
            By.XPATH, '//*[@id="production_table"]/tbody/tr/td[2]/span/span/a[1]'
        )
    ]
    resources = [
        int(resource.text.replace(".", ""))
        for resource in driver.find_elements(
            By.XPATH, '//*[@id="production_table"]/tbody/tr/td[4]/span'
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


def open_daily_bonus(driver: webdriver.Chrome, settings: dict):
    """Check and open once a day daily bonus"""

    if "bonus_opened" in settings:
        if settings["bonus_opened"] == time.strftime("%d.%m.%Y", time.localtime()):
            return

    def open_all_available_chests() -> None:
        bonuses = driver.find_elements(
            By.XPATH,
            '//*[@id="daily_bonus_content"]/div/div/div/div/div[@class="db-chest unlocked"]/../div[3]/a',
        )
        for bonus in bonuses:
            driver.execute_script("arguments[0].click()", bonus)

    # Daily bonus page address
    daily_bonus_url = (
        f"https://{settings['server_world']}.plemiona.pl/game.php?village="
    )
    village_id = driver.execute_script("return game_data.village.id;")
    daily_bonus_url += str(village_id) + "&screen=info_player&mode=daily_bonus"
    driver.get(daily_bonus_url)
    try:
        open_all_available_chests()
    except StaleElementReferenceException:
        open_all_available_chests()

    settings["bonus_opened"] = time.strftime("%d.%m.%Y", time.localtime())


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
            for id in driver.find_elements(
                By.XPATH,
                '//*[@id="villages_list"]/tbody/tr/td[1]/table/tbody/tr/td[1]/span',
            )
        ],
        "coords": [
            coords.text
            for coords in driver.find_elements(
                By.XPATH, '//*[@id="villages_list"]/tbody/tr/td[3]'
            )
        ],
    }

    return villages


def premium_exchange(driver: webdriver.Chrome, settings: dict) -> None:
    """Umożliwia automatyczną sprzedaż lub zakup surwców za punkty premium"""

    current_village_id = int(
        driver.execute_script("return window.game_data.village.id")
    )
    url = driver.current_url
    url = url[: url.rfind("/")]
    # Check if has premium account
    if driver.execute_script("return premium"):
        player_production_url = (
            url
            + f"/game.php?village={current_village_id}&screen=overview_villages&mode=prod&group=0&page=-1&"
        )

        def get_player_production_page() -> str:
            return driver.execute_script(
                f"""
                var request = new XMLHttpRequest();
                request.open("GET", "{player_production_url}", false);
                request.send(null);   
                return request.responseText;"""
            )

        try:
            html_response = get_player_production_page()
        except BaseException:
            log_in(driver=driver, settings=settings)
            captcha_check(driver=driver, settings=settings)
            html_response = get_player_production_page()
        doc = lxml.html.fromstring(html_response)
        try:
            production = doc.get_element_by_id("production_table")
        except:
            driver.get(player_production_url)
            if captcha_check(driver=driver, settings=settings):
                if not driver.find_elements(By.ID, "production_table"):
                    driver.get(player_production_url)
            doc = lxml.html.fromstring(driver.page_source)
            production = doc.get_element_by_id("production_table")

        villages = {}
        for village_data in production[1:]:
            village_id = village_data.xpath("td[2]/span")[0].get("data-id")
            village_market_url = (
                f"{url}/game.php?village={village_id}&screen=market&mode=exchange"
            )
            village_coords = village_data.xpath("td[2]/span/span/a/span")[0].text
            village_coords = re.findall(r"\d{3}\|\d{3}", village_coords)[-1]
            continent = f"k{village_coords[4]}{village_coords[0]}"
            if continent not in villages:
                villages[continent] = []
            village_resources = {}
            for resource_name, resource_amount in zip(
                ("wood", "stone", "iron"), village_data.xpath("td[4]/span")
            ):
                village_resources[resource_name] = int(
                    resource_amount.text_content().replace(".", "")
                )
            market_merchant = village_data.xpath("td[6]")[0].text_content().split("/")
            market_merchant = {
                "available": int(market_merchant[0]),
                "max": int(market_merchant[1]),
            }
            villages[continent].append(
                {
                    "coords": village_coords,
                    "resources": village_resources,
                    "market_url": village_market_url,
                    "market_merchant": market_merchant,
                }
            )
        for villages_by_continent in villages.values():
            villages_by_continent.sort(
                reverse=True,
                key=lambda v: sum(v["resources"].values())
                + v["market_merchant"]["available"] * 2000,
            )
    else:
        ...

    # Core loop iterate over all villages
    for continent, village_list in villages.items():
        # Skip continents marked as excluded
        if any(
            con in settings["market"]["market_exclude_villages"]
            for con in (continent, continent.upper())
        ):
            continue

        for village in village_list:
            market_url, village_coords = village["market_url"], village["coords"]

            if village_coords in settings["market"]["market_exclude_villages"]:
                continue

            # Skip if there is no market built or no merchant available
            if not village["market_merchant"]["available"]:
                continue

            for resource in village["resources"]:
                village["resources"][resource] -= settings["market"][resource][
                    "leave_in_storage"
                ]
            # If village does not have enough resources skip to next one
            if all(resource < 1 for resource in village["resources"].values()):
                continue

            driver.get(market_url)

            send_troops_in_the_middle(driver=driver, settings=settings)

            captcha_check(driver=driver, settings=settings)

            # Close chat
            driver.execute_script(
                'document.getElementById("chat-wrapper").innerHTML = "";'
            )

            exchange_doc = lxml.html.fromstring(
                driver.find_element(
                    By.XPATH, '//*[@id="premium_exchange_form"]/table/tbody'
                ).get_attribute("innerHTML")
            )
            exchange_resources = {
                resource_name: {
                    "current_resource_rate": 0,
                    "max_exchange_resource_can_receive": 0,
                }
                for resource_name in village["resources"]
            }
            for resource in village["resources"]:
                resource_capacity = exchange_doc.get_element_by_id(
                    f"premium_exchange_capacity_{resource}"
                ).text
                resource_stock = exchange_doc.get_element_by_id(
                    f"premium_exchange_stock_{resource}"
                ).text
                exchange_resources[resource]["max_exchange_resource_can_receive"] = int(
                    resource_capacity
                ) - int(resource_stock)
                resource_rate = driver.find_element(
                    By.XPATH, f'//*[@id="premium_exchange_rate_{resource}"]/div[1]'
                ).text
                exchange_resources[resource]["current_resource_rate"] = int(
                    resource_rate
                )

            # If market is full break current loop and go to next continent
            if all(
                not exchange_resources[resource_name][
                    "max_exchange_resource_can_receive"
                ]
                for resource_name in exchange_resources
            ):
                break
            # If all exchange rate is bigger than all max exchange rate user settings
            if all(
                exchange_resources[resource_name]["current_resource_rate"]
                > settings["market"][resource_name]["max_exchange_rate"]
                for resource_name in exchange_resources
            ):
                break

            SUM_EXCHANGE_RATE = sum(
                resource["current_resource_rate"]
                for resource in exchange_resources.values()
            )

            STARTING_TRANSPORT_CAPACITY = village["market_merchant"]["available"] * 1000
            transport_capacity = STARTING_TRANSPORT_CAPACITY

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
                            village["resources"][resource_name],
                        )
                    )

                    current_exchange_rate = int(
                        driver.find_element(
                            By.XPATH,
                            f'//*[@id="premium_exchange_rate_{resource_name}"]/div[1]',
                        ).text
                    )
                    if (
                        current_exchange_rate
                        > settings["market"][resource_name]["max_exchange_rate"]
                        # Pomiń jeśli kurs jest powyżej ustalonej wartości
                        or current_exchange_rate >= village["resources"][resource_name]
                    ):  # Pomiń jeśli kurs jest wyższy od dostępnych surowców
                        continue
                    # For the lowest exchange rate
                    if exchange_rate == min_exchange_rate:
                        if resource_to_sell > int(
                            max_exchange_rate
                            / SUM_EXCHANGE_RATE
                            * STARTING_TRANSPORT_CAPACITY
                        ):
                            resource_to_sell = int(
                                max_exchange_rate
                                / SUM_EXCHANGE_RATE
                                * STARTING_TRANSPORT_CAPACITY
                            )
                    # For the highest exchange rate
                    elif exchange_rate == max_exchange_rate:
                        if resource_to_sell > int(
                            min_exchange_rate
                            / SUM_EXCHANGE_RATE
                            * STARTING_TRANSPORT_CAPACITY
                        ):
                            resource_to_sell = int(
                                min_exchange_rate
                                / SUM_EXCHANGE_RATE
                                * STARTING_TRANSPORT_CAPACITY
                            )
                    # For medium exchange rate
                    else:
                        if resource_to_sell > int(
                            exchange_rate
                            / SUM_EXCHANGE_RATE
                            * STARTING_TRANSPORT_CAPACITY
                        ):
                            resource_to_sell = int(
                                exchange_rate
                                / SUM_EXCHANGE_RATE
                                * STARTING_TRANSPORT_CAPACITY
                            )
                    resource_to_sell -= current_exchange_rate
                    if resource_to_sell < 1:
                        # Check if still can sell cheaper than exchange rate
                        # which is available when market is almost full
                        if current_exchange_rate < max_resource_to_sell:
                            continue
                        resource_to_sell = 1

                    input = driver.find_element(
                        By.XPATH,
                        f'//*[@id="premium_exchange_sell_{resource_name}"]/div[1]/input',
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
                        driver.find_element(
                            By.XPATH, '//*[@id="premium_exchange_form"]/input'
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
                    ) or (
                        resource_to_sell == 1
                        and final_resource_amount_to_sell
                        > village["resources"][resource_name]
                    ):
                        driver.find_element(
                            By.CLASS_NAME, "btn.evt-cancel-btn.btn-confirm-no"
                        ).click()
                        input.clear()
                        continue

                    if (
                        final_resource_amount_to_sell
                        > village["resources"][resource_name]
                    ):
                        current_exchange_rate = driver.find_element(
                            By.XPATH, '//*[@id="confirmation-msg"]/div/p[2]'
                        ).text
                        current_exchange_rate = ceil(
                            final_resource_amount_to_sell
                            / int(re.search(r"\d+", current_exchange_rate).group())
                        )

                        driver.find_element(
                            By.CLASS_NAME, "btn.evt-cancel-btn.btn-confirm-no"
                        ).click()  # Click cancel button

                        final_resource_amount_to_sell = (
                            village["resources"][resource_name] - current_exchange_rate
                        )
                        if final_resource_amount_to_sell < 1:
                            if current_exchange_rate < max_resource_to_sell:
                                input.clear()
                                continue
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

    code = driver.find_element(
        By.XPATH, '//*[@id="withdraw_selected_units_village_info"]/table/tbody'
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
            ele = driver.find_element(
                By.XPATH,
                f'//*[@id="withdraw_selected_units_village_info"]/table/tbody/tr[{index+2}]/td[{temp[index][row][0]}]',
            )
            html = temp[index][row][1][temp[index][row][1].find("<") : -5]
            html = html[: html.find("value")] + 'value="" ' + html[html.find("min") :]
            driver.execute_script(f"""arguments[0].innerHTML = '{html}';""", ele)


def send_troops(driver: webdriver.Chrome, settings: dict) -> tuple[int, list]:
    """Send troops at given time.
    It can be attack or help.
    You can also use it for fakes.
    """

    # If for some reason there was func send_troops in to_do but there wasn't any
    # in settings["scheduler"]["ready_schedule"] than log error and return
    if not settings["scheduler"]["ready_schedule"]:
        stack_message = "Called empty settings['scheduler']['ready_schedule']\n"
        stack_message += "".join(line for line in traceback.format_stack(limit=3))
        logger.error(stack_message)
        return 0, []
    send_time = settings["scheduler"]["ready_schedule"][0]["send_time"]
    list_to_send = []
    for cell_in_list in settings["scheduler"]["ready_schedule"]:
        if cell_in_list["send_time"] > send_time + 8:
            break
        list_to_send.append(cell_in_list)

    if len(list_to_send) > 1:
        origin_tab = driver.current_window_handle
        new_tabs = []

    attacks_to_repeat_to_do = []  # Add to main to_do list -> self.to_do
    attacks_to_repeat_scheduler = []  #  Add to ["scheduler"]["ready_schedule"]
    try:
        for index, send_info in enumerate(list_to_send):

            if index:
                previous_tabs = set(driver.window_handles)
                # Open new tab
                driver.switch_to.new_window("tab")
                driver.get(send_info["url"])
                # Search and get new tab
                new_tab = set(driver.window_handles).difference(previous_tabs)
                new_tabs.append(*new_tab)
            else:
                driver.get(send_info["url"])

            # Check if place is build
            if driver.execute_script(
                "if (game_data.village.buildings.place==0) {return true}"
            ):
                if len(list_to_send) == 1:
                    return 1, []
                else:
                    continue

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
                        and send_info["snob_amount"] > 1
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
                            if settings["world_config"]["archer"] == 0:
                                if troop in ("archer", "marcher"):
                                    continue
                            if troop == "snob":
                                continue
                            input_field = driver.find_element(
                                By.ID, f"unit_input_{troop}"
                            )
                            troop_number = int(
                                input_field.get_attribute("data-all-count")
                            )
                            if troop_number == 0:
                                continue
                            match troop:
                                case "ram" | "catapult" | "knight":
                                    pass
                                case _:
                                    troop_number = round(
                                        troop_number
                                        / 100
                                        * send_info["first_snob_army_size"]
                                    )
                            input_field.send_keys(troop_number)

                    else:
                        # Choose all troops to send with exceptions
                        match send_info["army_type"]:

                            case "only_off":

                                choose_all_units_with_exceptions(troops_dict=troops_off)

                            case "only_deff":

                                choose_all_units_with_exceptions(
                                    troops_dict=troops_deff
                                )

                    if send_info["send_snob"] == "send_snob":
                        if send_info["snob_amount"]:
                            snob_input = driver.find_element(By.ID, "unit_input_snob")
                            snob_input.clear()
                            snob_input.send_keys("1")
                            send_info["snob_amount"] = send_info["snob_amount"] - 1

                case "send_fake":
                    # Choose troops to send
                    java_script = f'return Math.floor(window.game_data.village.points*{settings["world_config"]["fake_limit"]}/100)'
                    min_population = driver.execute_script(java_script)
                    current_population = 0
                    for troop_name, template_data in send_info["fake_template"].items():
                        troop_input = driver.find_element(
                            By.ID, f"unit_input_{troop_name}"
                        )
                        available_troop_number = int(
                            troop_input.get_attribute("data-all-count")
                        )
                        if (
                            available_troop_number >= template_data["min_value"]
                            and available_troop_number <= template_data["max_value"]
                        ):
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
                                if not available_troop_number:
                                    continue
                                troop_number = available_troop_number
                                current_population += (
                                    available_troop_number * template_data["population"]
                                )
                        elif available_troop_number >= template_data["max_value"]:
                            if (
                                template_data["max_value"] * template_data["population"]
                                >= min_population - current_population
                            ):
                                troop_number = ceil(
                                    (min_population - current_population)
                                    / template_data["population"]
                                )
                                current_population = min_population
                            else:
                                troop_number = template_data["max_value"]
                                current_population += (
                                    template_data["max_value"]
                                    * template_data["population"]
                                )
                        else:  # available_troop_number < template_data["min_value"]
                            return len(list_to_send), attacks_to_repeat_to_do
                        troop_input.send_keys(troop_number)
                        if current_population >= min_population:
                            break
                    # Not enough troops
                    else:
                        if len(list_to_send) == 1:
                            return 1, attacks_to_repeat_to_do
                        continue

                case "send_my_template":
                    # Choose troops to send
                    for troop_name, troop_number in send_info["troops"].items():
                        if not troop_number:
                            continue
                        if troop_number == "max":
                            driver.execute_script(
                                f'document.getElementById("units_entry_all_{troop_name}").click();'
                            )
                            continue
                        troop_input = driver.find_element(
                            By.ID, f"unit_input_{troop_name}"
                        )
                        troop_input.send_keys(troop_number)

                    if send_info["repeat_attack"]:
                        if send_info["total_attacks_number"]:
                            total_attacks_number = send_info["total_attacks_number"]
                            if total_attacks_number > 1:
                                total_attacks_number -= 1
                                # Add dict to list of attacks to repeat and in the end add to self.to_do
                                attacks_to_repeat_to_do.append(
                                    {
                                        "func": "send_troops",
                                        "start_time": send_info["send_time"]
                                        + 2 * send_info["travel_time"]
                                        + 1,
                                        "server_world": settings["server_world"],
                                        "settings": settings,
                                        "errors_number": 0,
                                    }
                                )
                                # Add the same attack to scheduler with changed send_time etc.
                                attack_to_add = send_info.copy()
                                if total_attacks_number == 1:
                                    attack_to_add["repeat_attack"] = 0
                                attack_to_add[
                                    "total_attacks_number"
                                ] = total_attacks_number
                                attack_to_add["send_time"] += (
                                    2 * send_info["travel_time"] + 9
                                )
                                arrival_time_in_sec = (
                                    attack_to_add["send_time"]
                                    + send_info["travel_time"]
                                )
                                arrival_time = time.localtime(arrival_time_in_sec)
                                attack_to_add["arrival_time"] = time.strftime(
                                    f"%d.%m.%Y %H:%M:%S:{round(random.random()*1000):0>3}",
                                    arrival_time,
                                )
                                attack_to_add["errors_number"] = 0
                                attacks_to_repeat_scheduler.append(attack_to_add)

            # Click command_type button (attack or support)
            driver.execute_script(
                f'document.getElementById("{send_info["command"]}").click();'
            )

            # Add snoob -> send_all
            if send_info["template_type"] == "send_all":
                if "snob_amount" in send_info:
                    try:
                        add_snoob = driver.find_element(By.ID, "troop_confirm_train")
                    except:
                        # Go to next attack if current can't be send
                        if len(list_to_send) > 1:
                            continue
                        # If it's only one attack which can't be send, return and delete it
                        return 1, attacks_to_repeat_to_do
                    for _ in range(send_info["snob_amount"]):
                        driver.execute_script("arguments[0].click()", add_snoob)

            # Split attacks -> own_template
            elif send_info["template_type"] == "send_my_template":
                if (
                    "split_attacks_number" in send_info
                    and send_info["split_attacks_number"] != 1
                ):
                    split_attacks_number = send_info["split_attacks_number"]
                    try:
                        add_attack = driver.find_element(By.ID, "troop_confirm_train")
                    except:
                        # Go to next attack if current can't be send
                        if len(list_to_send) > 1:
                            continue
                        # If it's only one attack which can't be send, return and delete it
                        return 1, attacks_to_repeat_to_do
                    for _ in range(split_attacks_number - 1):
                        driver.execute_script("arguments[0].click()", add_attack)
                    all_troops = (
                        "axe",
                        "light",
                        "snob",
                    )
                    for troop_name in all_troops:
                        if troop_name not in send_info["troops"]:
                            send_info["troops"][troop_name] = "0"
                    for troop_name, troop_number in send_info["troops"].items():
                        if troop_name == "snob" and troop_number == 1:
                            continue
                        for index in range(2, split_attacks_number + 1):
                            troop_input = driver.find_element(
                                By.NAME, f"train[{index}][{troop_name}]"
                            )
                            driver.execute_script(
                                f'arguments[0].value = "";', troop_input
                            )
                            if troop_number:
                                troop_input.send_keys(troop_number)

        if len(list_to_send) > 1:
            driver.switch_to.window(origin_tab)

        for index, send_info in enumerate(list_to_send):
            if index:
                driver.switch_to.window(new_tabs[index - 1])
            # Skip to next if didn't find element with id="date_arrival"
            current_time = driver.find_elements(
                By.XPATH, '//*[@id="date_arrival"]/span'
            )
            if not current_time:
                continue
            # If can choose catapult target
            if driver.execute_script(
                """
                catapult_target_select = document.getElementById('place_confirm_catapult_target');
                if (catapult_target_select && catapult_target_select.getAttribute('style')==null) {return true}
                else {return false}
                """
            ):
                if (
                    "catapult_target" in send_info
                    and "Default" not in send_info["catapult_target"]
                ):
                    Select(
                        driver.find_element(By.XPATH, "//select[@name='building']")
                    ).select_by_value(send_info["catapult_target"])
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
                    sec = ms / 1000
                if "low_priority" in send_info:
                    if send_info["low_priority"]:
                        driver.execute_script("arguments[0].click()", send_button)
                        continue
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

    finally:
        if len(list_to_send) > 1:
            time.sleep(0.5)
            for new_tab in new_tabs:
                driver.switch_to.window(new_tab)
                driver.close()
            driver.switch_to.window(origin_tab)

    for attack_to_repeat in attacks_to_repeat_scheduler:
        settings["scheduler"]["ready_schedule"].append(attack_to_repeat)

    return len(list_to_send), attacks_to_repeat_to_do


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

    # Variable send_number_times have to be equal or greater than 1
    index_to_del = []
    for index, row_data in enumerate(to_do):
        if row_data["func"] != "send_troops":
            continue
        if row_data["server_world"] != settings["server_world"]:
            continue
        index_to_del.append(index)
        if len(index_to_del) >= send_number_times:
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
        if captcha_check(driver=driver, settings=settings):
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
                webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
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
        elif driver.find_elements(
            By.XPATH, '//*[@id="open_groups"][@style="display: none;"]'
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
