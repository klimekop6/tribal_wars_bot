import ctypes
import json
import os
import re
import subprocess
import sys
import threading
import time
import winreg
from typing import TYPE_CHECKING

import compress_json
import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium_stealth import stealth
from ttkbootstrap.toast import ToastNotification
from webdriver_manager.chrome import ChromeDriverManager

from app.config import TWO_CAPTCHA_API_KEY
from app.decorators import log_errors
from app.logging import get_logger
from app.translator import TranslatorsServer
from gui.functions import custom_error, set_default_entries
from gui.windows.new_world import NewWorldWindow

if TYPE_CHECKING:
    from gui.windows.main import MainWindow

logger = get_logger(__name__)


def base_url(settings: dict) -> str:
    return f"https://{settings['server_world']}.{settings['game_url']}/game.php?"


@log_errors(re_raise=True)
def captcha_check(driver: webdriver.Chrome, settings: dict[str]) -> bool:
    """Check for captcha existence.

    If exist, wait until solved and than update captcha counter.
    """

    def captcha_on_page():
        return driver.execute_script(
            'return document.querySelector(".h-captcha, .captcha")'
        )

    if captcha_on_page():
        # Skip if it is not logged on page correctly
        if f"{settings['server_world']}" not in driver.current_url:
            return False

        def get_hcaptcha_selector() -> str:
            return driver.execute_script(
                """if (document.querySelector('.h-captcha')) {return '.h-captcha'}
                else if (document.querySelector('.captcha')) {return '.captcha'}
                else {return}
                """
            )

        captcha_selector = get_hcaptcha_selector()
        if not driver.find_elements(By.CSS_SELECTOR, f"{captcha_selector} iframe"):
            return False

        logger.info("start solving captcha")

        def simple_solve_hcaptcha(captcha_selector: str) -> bool:
            # Scroll to the element with class name equal to captche_selector
            driver.execute_script(
                f"document.querySelector('{captcha_selector}').scrollIntoView(false);"
            )
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
                WebDriverWait(driver, 5, 0.1).until(
                    lambda _: False if captcha_on_page() else True
                )
                return True
            except TimeoutException:
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                return False

        def get_hcaptcha_token(captcha_selector: str) -> str | bool:
            def get_hcaptcha_sitekey() -> str:
                return re.search(
                    r"&sitekey=(.*?)&",
                    WebDriverWait(driver, 3, 0.05)
                    .until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, f"{captcha_selector} iframe")
                        )
                    )
                    .get_attribute("src"),
                ).group(1)

            def data_to_solve_captcha() -> dict:
                return {
                    "key": TWO_CAPTCHA_API_KEY,
                    "method": "hcaptcha",
                    "sitekey": get_hcaptcha_sitekey(),
                    "pageurl": driver.current_url[: driver.current_url.rfind("/")],
                    "json": 1,
                }

            def handle_api_error(error_msg: str) -> bool:
                match error_msg:
                    case "ERROR_NO_SLOT_AVAILABLE":
                        time.sleep(5)
                    case "ERROR_ZERO_BALANCE":
                        time.sleep(60)
                    case "MAX_USER_TURN":
                        time.sleep(15)
                    case _:
                        logger.info(error_msg)
                        return False
                return True

            def start_solving(required_data: dict) -> dict:
                response = requests.post(
                    url="http://2captcha.com/in.php", json=required_data
                ).json()
                while not response["status"]:
                    if handle_api_error(response["request"]):
                        response = requests.post(
                            url="http://2captcha.com/in.php", json=required_data
                        ).json()
                    else:
                        return {"status": 0}
                return response

            def get_result(task_id: str) -> dict:
                start_time = time.time()
                time.sleep(15)
                data = {
                    "key": "88cda22298739b2fd3835ef281692c02",
                    "action": "get",
                    "id": int(task_id),
                    "json": 1,
                }
                response: dict = requests.get(
                    url="http://2captcha.com/res.php", params=data
                ).json()
                while not response["status"]:
                    if time.time() - start_time > 120:
                        return {"status": 0, "request": "ERROR_TIMEOUT"}
                    time.sleep(5)
                    response = requests.get(
                        url="http://2captcha.com/res.php", params=data
                    ).json()
                return response

            def notify_user_about_solving_process() -> None:
                try:
                    iframe_width = driver.execute_script(
                        f"return document.querySelector('{captcha_selector} iframe').clientWidth"
                    )
                except Exception:
                    iframe_width = 303
                driver.execute_script(
                    f"""const captcha_container = document.querySelectorAll("{captcha_selector} *:last-child")[0];
                    const div_to_add = "<div id='kspec' style='width: {iframe_width};'>Solving captcha please wait..</div>"
                    captcha_container.insertAdjacentHTML("afterend", div_to_add);"""
                )

            notify_user_about_solving_process()

            response = start_solving(required_data=data_to_solve_captcha())
            if not response["status"]:
                return False

            response = get_result(task_id=response["request"])
            if not response["status"]:
                logger.info(response["request"])
                return False

            return response["request"]

        def hard_solve_hcaptcha_using_token(captcha_selector: str) -> bool:
            token = get_hcaptcha_token(captcha_selector)
            try:
                driver.execute_script("document.querySelector('#kspec').remove();")
            except Exception:
                logger.info("Unable to find #kspec div")
            if token:
                try:
                    driver.execute_script(
                        f"document.getElementById('anycaptchaSolveButton').onclick('{token}');"
                    )
                except Exception:
                    logger.info("Unable to find 'anycaptchaSolveButton'")
                    return False
                return True
            return False

        def hard_solve_hcaptcha_using_grid(captcha_selector: str) -> bool:
            def switch_to_captcha_entry_iframe() -> None:
                driver.switch_to.default_content()
                WebDriverWait(driver, 5, 0.05).until(
                    EC.frame_to_be_available_and_switch_to_it(
                        (By.CSS_SELECTOR, f"{captcha_selector} iframe")
                    )
                )

            def select_checkbox() -> None:
                try:
                    driver.find_element(By.ID, "checkbox").click()
                finally:
                    driver.switch_to.default_content()

            def switch_to_captcha_challenge_frame() -> None:
                driver.switch_to.default_content()
                hcaptcha_frames = lambda: driver.find_elements(
                    By.XPATH, '//iframe[contains(@title, "hCaptcha")]'
                )
                driver.switch_to.frame(
                    WebDriverWait(driver, 5, 0.05).until(
                        lambda _: len(hcaptcha_frames()) > 1
                        and hcaptcha_frames()[1].is_displayed()
                        and hcaptcha_frames()[1]
                    )
                )

            def data_to_solve_captcha() -> dict:
                return {
                    "key": "88cda22298739b2fd3835ef281692c02",
                    "method": "base64",
                    "recaptcha": 1,
                    "body": image_base64(),
                    "textinstructions": instruction_text(),
                    "imginstructions": instruction_image(),
                    "recaptcharows": 3,
                    "recaptchacols": 3,
                    "json": 1,
                    "language": 2,
                    "lang": "en",
                }

            def image_base64():
                return (
                    WebDriverWait(driver, 5)
                    .until(EC.element_to_be_clickable((By.CLASS_NAME, "task-grid")))
                    .screenshot_as_base64
                )

            def instruction_text() -> str:
                if instruction_lang() == "en":
                    return driver.find_element(By.CLASS_NAME, "prompt-text").text
                try:
                    return TranslatorsServer().bing(
                        driver.find_element(By.CLASS_NAME, "prompt-text").text
                    )
                except Exception:
                    logger.error("Translation error")
                    return "translation error, try to use image instruction"

            def instruction_image():
                return (
                    WebDriverWait(driver, 5)
                    .until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "challenge-example"))
                    )
                    .screenshot_as_base64
                )

            def instruction_lang() -> str:
                return driver.find_element(
                    By.CSS_SELECTOR, ".display-language div"
                ).text.lower()

            def start_solving(required_data: dict) -> dict:
                response = requests.post(
                    url="http://2captcha.com/in.php", json=required_data
                ).json()
                while not response["status"]:
                    if handle_api_error(response["request"]):
                        response = requests.post(
                            url="http://2captcha.com/in.php", json=required_data
                        ).json()
                    else:
                        return {"status": 0}
                return response

            def handle_api_error(error_msg: str) -> bool:
                match error_msg:
                    case "ERROR_NO_SLOT_AVAILABLE":
                        time.sleep(5)
                    case "ERROR_ZERO_BALANCE":
                        time.sleep(60)
                    case "MAX_USER_TURN":
                        time.sleep(15)
                    case _:
                        logger.info(error_msg)
                        return False
                return True

            def get_result(task_id: str) -> dict:
                start_time = time.time()
                time.sleep(10)
                data = {
                    "key": "88cda22298739b2fd3835ef281692c02",
                    "action": "get",
                    "id": int(task_id),
                    "json": 1,
                }
                response: dict = requests.get(
                    url="http://2captcha.com/res.php", params=data
                ).json()
                while not response["status"]:
                    if time.time() - start_time > 120:
                        return {"status": 0, "request": "ERROR_TIMEOUT"}
                    time.sleep(5)
                    response = requests.get(
                        url="http://2captcha.com/res.php", params=data
                    ).json()
                return response

            def select_captcha_images(images_to_click: str) -> None:
                images_to_click = tuple(
                    int(index)
                    for index in images_to_click.replace("click:", "").split("/")
                )
                for index, image in enumerate(
                    driver.find_elements(By.CSS_SELECTOR, ".task-grid .task-image"),
                    start=1,
                ):
                    if index in images_to_click:
                        time.sleep(0.05)
                        image.click()

            def submit() -> None:
                time.sleep(0.5)
                driver.find_element(By.CSS_SELECTOR, ".button-submit.button").click()

            def get_is_successful() -> bool:
                switch_to_captcha_entry_iframe()
                anchor: WebElement = driver.find_element(
                    By.CSS_SELECTOR, "#anchor #checkbox"
                )
                for _ in range(6):
                    time.sleep(0.5)
                    checked = anchor.get_attribute("aria-checked")
                    if str(checked) == "true":
                        return True
                return False

            captcha_selector = get_hcaptcha_selector()
            switch_to_captcha_entry_iframe()
            select_checkbox()
            for _ in range(5):
                switch_to_captcha_challenge_frame()
                required_data = data_to_solve_captcha()
                response = start_solving(required_data)
                if not response["status"]:
                    break

                response = get_result(task_id=response["request"])
                if not response["status"]:
                    logger.info(response["request"])
                    break

                select_captcha_images(images_to_click=response["request"])
                submit()
                if get_is_successful():
                    return True

            return False

        try:
            if simple_solve_hcaptcha(captcha_selector):
                logger.info("captcha solved the easy way")
                return True

        except TimeoutException:
            driver.switch_to.default_content()
            driver.save_screenshot(
                f'logs/{time.strftime("%d.%m.%Y %H_%M_%S", time.localtime())}.png'
            )
            logger.error(f"error when solving the easy way\n {driver.current_url}")

        if not captcha_on_page():
            logger.info("captcha solved the easy way after error")
            return True

        if (
            driver.execute_script(
                "return document.getElementById('anycaptchaSolveButton')"
            )
            is None
        ):
            try:
                if hard_solve_hcaptcha_using_grid(captcha_selector):
                    logger.info("captcha solved the hard way using grid method")
                    settings["temp"]["captcha_counter"].set(
                        settings["temp"]["captcha_counter"].get() + 1
                    )
                    return True
            except Exception:
                logger.error("hcaptcha grid solver failed")
                driver.save_screenshot(
                    f'logs/{time.strftime("%d.%m.%Y %H_%M_%S", time.localtime())}.png'
                )
            finally:
                driver.switch_to.default_content()

        elif hard_solve_hcaptcha_using_token(captcha_selector):
            logger.info("captcha solved the hard way")
            time.sleep(1)
            driver.save_screenshot(
                f'logs/{time.strftime("%d.%m.%Y %H_%M_%S", time.localtime())}.png'
            )
            settings["temp"]["captcha_counter"].set(
                settings["temp"]["captcha_counter"].get() + 1
            )
            return True

        logger.info("error when dealing with captcha")
        driver.refresh()

        return True
    return False


def account_access(func) -> None:
    def wrapper(*args, **kwargs):
        settings = kwargs["settings"]
        tmp_driver = False
        if not kwargs["driver"]:
            driver = kwargs["driver"] = run_driver(settings=settings)
            logged_in = log_in(driver, settings)
            tmp_driver = True
        else:
            driver = kwargs["driver"]

        if (
            f"{settings['server_world']}.{settings['game_url']}"
            not in driver.current_url
        ):
            logged_in = False
            driver.get(log_in_game_url(settings))

        try:
            requirements_satisfied = func(*args, **kwargs)
        except Exception as exception:
            logger.error("error catched by decorator log_errors")

        if not requirements_satisfied:
            if tmp_driver:
                driver.quit()

            if not logged_in:
                driver.get("chrome://newtab")

            for combobox in kwargs["widget"]:
                combobox["values"] = ["Grupy niedost??pne"]
                combobox.set("Grupy niedost??pne")
            return

        if tmp_driver:
            driver.quit()
            return

        if not logged_in:
            driver.get("chrome://newtab")

        return

    return wrapper


@account_access
def check_groups(
    driver: webdriver.Chrome, settings: dict[str], widgets: list | tuple, **kwargs
) -> bool:
    """Sprawdza dost??pne grupy i zapisuje je w settings.json"""

    if not driver.execute_script("return premium"):
        return False

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
    for combobox in widgets:
        combobox["values"] = settings["groups"]

    return True


def chrome_profile_path(settings: dict) -> None:
    """Wyszukuj?? i zapisuje w ustawieniach aplikacji aktualn?? ??cierzk?? do profilu u??ytkownika przegl??darki chrome"""

    path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\TribalWars")
    settings["path"] = path

    with open("settings.json", "w") as settings_json_file:
        json.dump(settings, settings_json_file)


def delegate_things_to_other_thread(
    settings: dict, main_window: "MainWindow"
) -> threading.Thread:
    """Used to speedup app start doing stuff while connecting to database or API"""

    def add_new_default_settings(_settings: dict[str, dict]) -> None:
        _settings["gathering"].setdefault("auto_adjust", False)

        _settings.setdefault("coins", {"villages": {}})
        _settings["coins"].setdefault("villages", {})
        _settings["coins"].setdefault("mine_coin", False)
        _settings["coins"].setdefault("max_send_time", 120)

        _settings.setdefault("world_config", {})
        _settings["world_config"].setdefault("daily_bonus", None)

    def run_in_other_thread() -> None:

        # Load settings into settings_by_worlds[server_world]
        try:
            for settings_file_name in os.listdir("settings"):
                server_world = settings_file_name[: settings_file_name.find(".")]
                main_window.settings_by_worlds[server_world] = load_settings(
                    f"settings//{settings_file_name}"
                )
                add_new_default_settings(main_window.settings_by_worlds[server_world])
        except FileNotFoundError:
            os.mkdir("settings")

        # Add reference to deeper lists and dicts between settings and settings_by_worlds[server_world]
        if (
            "server_world" in settings
            and settings["server_world"] in main_window.settings_by_worlds
        ):
            settings.update(main_window.settings_by_worlds[settings["server_world"]])

    if not main_window.settings_by_worlds:
        threading.Thread(target=run_in_other_thread).start()


def expiration_warning(settings: dict, main_window: "MainWindow") -> None:

    time_to_expire = (
        time.mktime(
            time.strptime(
                main_window.user_data["active_until"] + " 23:59:59", "%Y-%m-%d %H:%M:%S"
            )
        )
        - time.time()
    )

    if 0 < time_to_expire < 86_400:
        ToastNotification(
            title="TribalWarsBot Warning",
            message="Wa??no???? twojego konta nied??ugo si?? sko??czy. ",
            topmost=True,
            bootstyle="warning",
        ).show_toast()
    elif time_to_expire > 86_400:
        main_window.master.after(
            ms=int(time_to_expire - 86_400),
            func=lambda: expiration_warning(settings=settings, main_window=main_window),
        )


def first_app_lunch(settings: dict) -> None:
    """Do some stuff if app was just installed for the 1st time"""

    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    if is_admin():
        # Code to run if has admin rights
        # Create app folder in registry to keep keys and data
        # HKEY_CURRENT_USER\Software\TribalWarsBot
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software") as key:
            winreg.CreateKey(key, "TribalWarsBot")
        chrome_profile_path(settings)
    else:
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, __file__, None, 1
        )
        sys.exit()


def first_app_login(settings: dict, main_window: "MainWindow") -> None:
    set_default_entries(entries=main_window.entries_content)
    NewWorldWindow(parent=main_window, settings=settings, obligatory=True)
    settings["first_lunch"] = False


def get_villages_id(settings: dict[str], update: bool = False) -> dict:
    """Download, process and save in text file for future use.
    In the end return all villages in the world with proper id.
    """

    def update_world_villages_file() -> None:
        """Create or update file with villages and their id's"""

        if update:
            file_name = f'villages{settings["server_world"]}.txt'
            creation_time = os.path.getmtime(file_name)
            if time.time() - creation_time < 3600:
                return

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
        update_world_villages_file()

    villages = {}
    try:
        world_villages_file = open(f'villages{settings["server_world"]}.txt')
    except FileNotFoundError:
        update_world_villages_file()
        world_villages_file = open(f'villages{settings["server_world"]}.txt')
    finally:
        for row in world_villages_file:
            village_coords, village_id = row.split(",")
            villages[village_coords] = village_id
        world_villages_file.close()

    return villages


def load_settings(file_path: str = "settings.json") -> dict:
    try:
        return compress_json.load(file_path)
    except FileNotFoundError:
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
        compress_json.dump(settings, "settings.json")
        return settings


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
            driver.get(log_in_game_url(settings))
        except WebDriverException as e:
            if "cannot determine loading status" in e.msg:
                pass

        # Czy prawid??owo wczytano i zalogowano si?? na stronie
        if f"{settings['server_world']}.{settings['game_url']}" in driver.current_url:
            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            return True

        # R??czne logowanie na stronie plemion
        elif f"https://www.{settings['game_url']}/" in driver.current_url:

            if not "game_user_name" in settings:
                if not driver.find_elements(By.ID, "login_form"):
                    return log_in(driver=driver, settings=settings)
                driver.switch_to.window(driver.current_window_handle)
                custom_error(
                    message="Zaloguj si?? na otwartej stronie plemion.\n"
                    "Pole zapami??taj mnie powinno by?? zaznaczone."
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
                    (By.XPATH, f'//span[text()="??wiat {settings["world_number"]}"]')
                )
            ).click()
            return True

        # Ponowne wczytanie strony w przypadku niepowodzenia (np. chwilowy brak internetu)
        else:
            for sleep_time in (5, 15, 60, 120, 300):
                time.sleep(sleep_time)
                driver.get(log_in_game_url(settings))
                if (
                    f"{settings['server_world']}.{settings['game_url']}"
                    in driver.current_url
                ):
                    return True

        log_error(driver, msg="bot_functions -> log_in no error raised")
        return False

    except Exception:
        log_error(driver, msg="bot_functions -> log_in error raised")
        return False


def paid(date: str) -> bool:
    """Return True if paid or False if not"""

    def current_time() -> str:
        return time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())

    if time.strptime(current_time(), "%d/%m/%Y %H:%M:%S") > time.strptime(
        date + " 23:59:59", "%Y-%m-%d %H:%M:%S"
    ):
        return False
    return True


def log_in_game_url(settings: dict) -> str:
    return f"https://www.{settings['game_url']}/page/play/{settings['server_world']}"


def run_driver(settings: dict) -> webdriver.Chrome:
    """Uruchamia sterownik i przegl??dark?? google chrome"""

    try:
        chrome_options = Options()
        chrome_options.add_argument(f'user-data-dir={settings["path"]}')
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        if settings["globals"]["disable_chrome_background_throttling"]:
            chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_extension(
            extension="browser_extensions//captcha_callback_hooker.crx"
        )
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-automation", "disable-popup-blocking"]
        )
        while True:
            try:
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager(cache_valid_range=7).install()),
                    options=chrome_options,
                )
                break
            except:
                time.sleep(2)
                subprocess.run(
                    "taskkill /IM chromedriver.exe /F /T",
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                time.sleep(3)
        return driver
    except Exception as exc:
        logger.error(exc)

    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )


def save_settings_to_files(settings: dict, settings_by_worlds: dict) -> None:
    # Make sure that settings is saved in correct self.settings_by_worlds
    if "server_world" in settings and settings["server_world"] in settings_by_worlds:
        settings_by_worlds[settings["server_world"]].update(
            (k, v) for k, v in settings.items() if k != "globals"
        )

    # Settings per server_world save in file
    for server_world in settings_by_worlds:
        _settings = settings_by_worlds[server_world]
        if "temp" in _settings:
            del _settings["temp"]
        compress_json.dump(_settings, f"settings/{server_world}.json")

    # Initial/global settings save in file
    if "temp" in settings:
        del settings["temp"]
    settings["scheduler"]["ready_schedule"] = []
    compress_json.dump(settings, "settings.json")


def unwanted_page_content(
    driver: webdriver.Chrome, settings: dict[str], html: str = "", log: bool = True
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
            or settings["server_world"] not in driver.current_url
        ):
            return log_in(driver, settings)

        # If captcha on page
        if captcha_check(driver=driver, settings=settings):
            return True

        # Bonus dzienny i pozosta??e okna nale??ac?? do popup_box_container
        elif html.find("popup_box_container") != -1:
            # Poczekaj do 2 sekund w celu wczytania ca??o??ci dynamicznego kontentu
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

                    except Exception:
                        return False

                # Pr??buj?? odebra?? bonus dzienny je??li si?? nie uda od??wie??a stron?? i pr??buj?? ponownie.
                # W razie niepowodzenia tworzy log b????du
                if open_daily_bonus():
                    return True

                driver.refresh()
                if open_daily_bonus():
                    return True

                log_error(
                    driver=driver, msg="unwanted_page_content -> open_daily_bonus"
                )
                return False

            # Zamknij wszystkie popup_boxy kt??re nie dotycz?? bonusu dziennego
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
            if log:
                log_error(driver=driver, msg="unwanted_page_content -> uknown error")
            return False

    except Exception:
        log_error(
            driver=driver,
            msg="unwanted_page_content -> error while handling common errors",
        )
        return False
