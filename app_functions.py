import ctypes
import json
import os
import re
import subprocess
import sys
import threading
import time
import winreg

import requests
from anycaptcha import AnycaptchaClient, HCaptchaTaskProxyless
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
from ttkbootstrap.toast import ToastNotification


from app_logging import get_logger
from config import ANY_CAPTCHA_API_KEY
from decorators import log_errors
from gui_functions import custom_error, set_default_entries

logger = get_logger(__name__)


@log_errors(re_raise=True)
def captcha_check(driver: webdriver.Chrome, settings: dict[str]) -> bool:
    """Check for captcha existence.

    If exist, wait until solved and than update captcha counter.
    """

    search_for_captcha = 'return document.querySelector(".h-captcha, .captcha")'
    if driver.execute_script(search_for_captcha):
        # Skip if it is not logged on page correctly
        if f"{settings['server_world']}" not in driver.current_url:
            return False

        get_captcha_selector = """if (document.querySelector('.h-captcha')) {return '.h-captcha'}
            else if (document.querySelector('.captcha')) {return '.captcha'}
            else {return}
            """
        captcha_selector = driver.execute_script(get_captcha_selector)
        if not driver.find_elements(By.CSS_SELECTOR, f"{captcha_selector} iframe"):
            return False

        logger.info("start solving captcha")

        def simple_solve_captcha(captcha_selector: str) -> bool:
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
                    lambda _: False
                    if driver.execute_script(search_for_captcha)
                    else True
                )
                return True
            except TimeoutException:
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                return False

        def get_token(captcha_selector: str) -> str | bool:

            api_key = ANY_CAPTCHA_API_KEY
            website_url = driver.current_url[: driver.current_url.rfind("/")]
            website_key = re.search(
                r"&sitekey=(.*?)&",
                WebDriverWait(driver, 3, 0.05)
                .until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, f"{captcha_selector} iframe")
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
            try:
                iframe_width = driver.execute_script(
                    f"return document.querySelector('{captcha_selector} iframe').clientWidth"
                )
            except BaseException:
                iframe_width = 303
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

        def hard_solve_captcha(captcha_selector: str) -> bool:
            token = get_token(captcha_selector)
            driver.execute_script("document.querySelector('#kspec').remove();")
            if token:
                driver.execute_script(
                    f"document.getElementById('anycaptchaSolveButton').onclick('{token}');"
                )
                return True
            return False

        try:
            if simple_solve_captcha(captcha_selector):
                logger.info("captcha solved the easy way")
                return True

        except TimeoutException:
            driver.switch_to.default_content()
            driver.save_screenshot(
                f'logs/{time.strftime("%d.%m.%Y %H_%M_%S", time.localtime())}.png'
            )
            logger.error(f"error when solving the easy way\n {driver.current_url}")

        if not driver.execute_script(search_for_captcha):
            logger.info("captcha solved the easy way after error")
            return True

        if hard_solve_captcha(captcha_selector):
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


def check_groups(driver: webdriver.Chrome, settings: dict[str], *args) -> None:
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


def chrome_profile_path(settings: dict) -> None:
    """Wyszukuję i zapisuje w ustawieniach aplikacji aktualną ścierzkę do profilu użytkownika przeglądarki chrome"""

    path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\TribalWars")
    settings["path"] = path

    with open("settings.json", "w") as settings_json_file:
        json.dump(settings, settings_json_file)


def delegate_things_to_other_thread(settings: dict, main_window) -> threading.Thread:
    """Used to speedup app start doing stuff while connecting to database or API"""

    def add_new_default_settings(_settings: dict) -> None:
        _settings.setdefault("coins", {"villages": {}})
        _settings["coins"].setdefault("villages", {})
        _settings["coins"].setdefault("mine_coin", False)
        _settings["coins"].setdefault("max_send_time", 120)

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


def expiration_warning(settings: dict, main_window) -> None:

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
            message="Ważność twojego konta niedługo się skończy. ",
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


def first_app_login(settings: dict, main_window) -> None:
    set_default_entries(entries=main_window.entries_content)
    main_window.add_new_world_window(settings=settings, obligatory=True)
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
        except WebDriverException as e:
            if "cannot determine loading status" in e.msg:
                pass

        # Czy prawidłowo wczytano i zalogowano się na stronie
        if f"{settings['server_world']}.{settings['game_url']}" in driver.current_url:
            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            return True

        # Ręczne logowanie na stronie plemion
        elif f"https://www.{settings['game_url']}/" in driver.current_url:

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


def paid(date: str) -> bool:
    """Return True if paid or False if not"""

    def current_time() -> str:
        return time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())

    if time.strptime(current_time(), "%d/%m/%Y %H:%M:%S") > time.strptime(
        date + " 23:59:59", "%Y-%m-%d %H:%M:%S"
    ):
        return False
    return True


def run_driver(settings: dict) -> webdriver.Chrome:
    """Uruchamia sterownik i przeglądarkę google chrome"""

    try:
        chrome_options = Options()
        chrome_options.add_argument(f'user-data-dir={settings["path"]}')
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_extension(
            extension="browser_extensions//captcha_callback_hooker.crx"
        )
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-automation", "disable-popup-blocking"]
        )
        while True:
            try:
                driver = webdriver.Chrome(
                    service=Service(
                        ChromeDriverManager(cache_valid_range=14).install()
                    ),
                    options=chrome_options,
                )
                # driver.execute_cdp_cmd(
                #     "Page.addScriptToEvaluateOnNewDocument",
                #     {"source": COORDS_COPY},
                # )
                break
            except:
                time.sleep(2)
                subprocess.run(
                    "taskkill /IM chromedriver.exe /F /T",
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                time.sleep(3)
        return driver
    except BaseException as exc:
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
        with open(f"settings/{server_world}.json", "w") as settings_json_file:
            json.dump(_settings, settings_json_file)

    # Initial/global settings save in file
    if "temp" in settings:
        del settings["temp"]
    settings["scheduler"]["ready_schedule"] = []
    with open("settings.json", "w") as settings_json_file:
        json.dump(settings, settings_json_file)


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
            if log:
                log_error(driver=driver, msg="unwanted_page_content -> uknown error")
            return False

    except BaseException:
        log_error(
            driver=driver,
            msg="unwanted_page_content -> error while handling common errors",
        )
        return False


# def on_new_tab(driver: webdriver.Chrome, settings: dict) -> None:
#     while True:
#         main_window = driver.current_window_handle
#         if "window" not in settings["temp"]:
#             settings["temp"]["window"] = []

#         switched = False
#         for window in driver.window_handles:
#             if window not in settings["temp"]["window"]:
#                 driver.switch_to.window(window)
#                 switched = True
#                 driver.execute_cdp_cmd(
#                     "Page.addScriptToEvaluateOnNewDocument",
#                     {"source": coords_copy},
#                 )
#                 settings["temp"]["window"].append(window)
#         if switched:
#             driver.switch_to.window(main_window)
#         time.sleep(0.1)
