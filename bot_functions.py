from distutils.log import error
import random
import re
import time
import traceback
import threading
from math import sqrt, ceil

import logging
import lxml.html
import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

import email_notifications

logging.basicConfig(filename='log.txt', level=logging.ERROR)


def attacks_labels(driver: webdriver, settings: dict[str], notifications: bool=False) -> bool:
    """Etykiety ataków"""
   
    if not driver.find_element_by_id('incomings_amount').text:
        return False
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'incomings_cell'))).click()  # Otwarcie karty z nadchodzącymi atakami
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[1]/*[@data-group-type="all"]'))).click()  # Zmiana grupy na wszystkie
    manage_filters = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a')))  # Zwraca element z filtrem ataków
    if driver.find_element_by_xpath('//*[@id="paged_view_content"]/div[2]').get_attribute('style').find('display: none') != -1:
        manage_filters.click()
    etkyieta_rozkazu = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[2]/td[2]/input')))
    etkyieta_rozkazu.clear()
    etkyieta_rozkazu.send_keys('Atak')
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[6]/td/input'))).click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a')))
    try:
        driver.find_element_by_id('incomings_table')
    except:
        return True

    element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'select_all')))
    driver.execute_script('return arguments[0].scrollIntoView(true);', element)
    element.click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//input[@value="Etykieta"]'))).click()

    if notifications:
        etkyieta_rozkazu = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[2]/td[2]/input')))
        etkyieta_rozkazu.clear()
        etkyieta_rozkazu.send_keys('Szlachcic')
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[6]/td/input'))).click()
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a')))
        if driver.find_elements_by_id('incomings_table'):
            number_of_attacks = driver.find_element_by_xpath('//*[@id="incomings_table"]/tbody/tr[1]/th[1]').text
            number_of_attacks = re.search(r'\d+', number_of_attacks).group()
            reach_time_list = [reach_time.text for reach_time in driver.find_elements_by_xpath('//*[@id="incomings_table"]/tbody/tr/td[6]')]
            attacks_reach_time = ''.join(f'{index+1}. {_}\n' for index, _ in enumerate(reach_time_list))
                    
            email_notifications.send_email(
                email_recepients=settings['notifications']['email_address'], 
                email_subject='Wykryto grubasy', 
                email_body=f'Wykryto grubasy o godzinie {time.strftime("%H:%M:%S %d.%m.%Y", time.localtime())}\n\n'
                           f'Liczba nadchodzących grubasów: {number_of_attacks}\n\n'
                           f'Godziny wejść:\n'
                           f'{attacks_reach_time}')

            current_time = time.strftime("%H:%M:%S %d.%m.%Y", time.localtime())

            for label in driver.find_elements_by_xpath('//*[@id="incomings_table"]/tbody/tr/td[1]/span/span/a[2]'):
                driver.execute_script('return arguments[0].scrollIntoView(true);', label)    
                label.click()

            for label_input in driver.find_elements_by_xpath('//*[@id="incomings_table"]/tbody/tr/td[1]/span/span[2]/input[1]'):
                label_input.clear()
                label_input.send_keys(f'szlachta notified {current_time}')
                label_input.send_keys(Keys.ENTER)

    return True


def auto_farm(driver: webdriver, settings: dict[str]) -> None:
    """Automatyczne wysyłanie wojsk w asystencie farmera""" 

    # Przechodzi do asystenta farmera
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'manager_icon_farm'))).click()

    # Sprawdza czy znajduję się w prawidłowej grupie jeśli nie to przechodzi do prawidłowej -> tylko dla posiadaczy konta premium
    if int(settings['account_premium']):
        driver.find_element_by_id('open_groups').click()
        current_group = WebDriverWait(driver, 10, 0.033).until(EC.presence_of_element_located((By.XPATH, '//*[@id="group_id"]/option[@selected="selected"]'))).text

        if current_group != settings['farm_group']:
            select = Select(driver.find_element_by_id('group_id'))
            select.select_by_visible_text(settings['farm_group'])
            WebDriverWait(driver, 10, 0.033).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="group_table"]/tbody/tr[1]/td[1]/a'))).click()
        close_group = driver.find_element_by_id('closelink_group_popup')
        driver.execute_script('return arguments[0].scrollIntoView(true);', close_group)
        close_group.click()
        WebDriverWait(driver, 2, 0.033).until(EC.presence_of_element_located((By.XPATH, '//*[@id="close_groups"][@style="display: none;"]')))

    # Początkowa wioska - format '(439|430) K44'
    starting_village = driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text

    while True:

        # Ukrywa chat
        chat = driver.find_element_by_xpath('//*[@id="chat-wrapper"]')
        driver.execute_script("arguments[0].innerHTML = '';", chat)

        # Szablon A i B nazwy jednostek i ich liczebność        
        doc = lxml.html.fromstring(driver.find_element_by_id('content_value').get_attribute('innerHTML'))
        template_troops = {
            'A': doc.xpath('div[2]/div/form/table/tbody/tr[2]/td/input'),
            'B': doc.xpath('div[2]/div/form/table/tbody/tr[4]/td/input')
            }

        for key in template_troops:
            tmp = {}
            for row in template_troops[key]:  
                troop_number = int(row.get('value'))
                if troop_number:                        
                    troop_name = row.get('name')
                    troop_name = re.search(r'[a-z]+', troop_name).group()
                    tmp[troop_name] = troop_number
            template_troops[key] = tmp

        # Unikalne nazwy jednostek z szablonów A i B
        troops_name = set(_key for key in template_troops for _key in template_troops[key].keys())

        # Aktualnie dostępne jednostki w wiosce
        doc = doc.xpath('//*[@id="units_home"]/tbody/tr[2]')[0]
        available_troops = {troop_name: int(doc.xpath(f'td[@id="{troop_name}"]')[0].text) for troop_name in troops_name}

        # Pomija wioskę jeśli nie ma z niej nic do wysłania
        skip = {'A': False, 'B': False}
        for template in template_troops:
            for troop_name, troop_number in template_troops[template].items():
                if available_troops[troop_name] - troop_number < 0:
                    skip[template] = True
                    break

        if skip['A'] and skip['B']:
            ActionChains(driver).send_keys('d').perform()
            if starting_village == driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text:
                break
            continue

        # Lista poziomów murów
        walls_level = driver.find_element_by_id('plunder_list').get_attribute('innerHTML').split('<tr')[3:]
        for index, row in enumerate(walls_level):
            walls_level[index] = row.split('<td')[7:8]
        for index, row in enumerate(walls_level):
            for ele in row:
                walls_level[index] = ele[ele.find('>')+1:ele.find('<')] 
        walls_level = [ele if ele=='?' else int(ele) for ele in walls_level]
        
        # Lista przycisków do wysyłki szablonów A, B i C
        villages_to_farm = {}
            
        if int(settings['A']['active']): 
            villages_to_farm['A'] = 9  # Szablon A
        if int(settings['B']['active']): 
            villages_to_farm['B'] = 10  # Szablon B
        if int(settings['C']['active']):     
            villages_to_farm['C'] = 11  # Szablon C

        # Wysyłka wojsk w asystencie farmera
        start_time = 0
        no_units = False        
        for index, template in enumerate(villages_to_farm):

            if skip[template]:
                continue            

            villages_to_farm[template] = driver.find_elements_by_xpath(f'//*[@id="plunder_list"]/tbody/tr/td[{villages_to_farm[template]}]/a')
            captcha_solved = False
            for village, wall_level in zip(villages_to_farm[template], walls_level): 
                if isinstance(wall_level, str) and not int(settings[template]['wall_ignore']):
                    continue        
                if int(settings[template]['wall_ignore']) or int(settings[template]['min_wall']) <= wall_level <= int(settings[template]['max_wall']):
                    for unit, number in template_troops[template].items():
                        if available_troops[unit]-number < 0:
                            no_units = True
                            break
                        available_troops[unit] -= number
                    if no_units:
                        break
                    html = driver.page_source
                    if html.find('captcha') != -1 and not captcha_solved:
                        driver.save_screenshot('before.png')
                        time.sleep(40)
                        driver.save_screenshot('after.png')
                        captcha_solved = True
                    while time.time()-start_time < 0.195:
                        time.sleep(0.01)
                    driver.execute_script('return arguments[0].scrollIntoView({block: "center"});', village)
                    village.click()
                start_time = time.time()
            if index < len(villages_to_farm)-1:
                no_units = False
                driver.refresh()                
                chat = driver.find_element_by_xpath('//*[@id="chat-wrapper"]')
                driver.execute_script("arguments[0].innerHTML = '';", chat)

        # Przełącz wioskę i sprawdź czy nie jest to wioska startowa
        ActionChains(driver).send_keys('d').perform()
        if starting_village == driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text:
            break


def check_groups(driver: webdriver, settings: dict[str], run_driver, *args) -> None:
    """Sprawdza dostępne grupy i zapisuje je w settings.json"""

    if not int(settings['account_premium']):
        for combobox in args:
            combobox['values'] = ['Grupy niedostępne']
            combobox.set('Grupy niedostępne')
        return

    tmp_driver = False
    if not driver:
        driver = run_driver(headless=True)
        log_in(driver, settings)
        tmp_driver = True

    logged_in = True
    if f'pl{settings["world_number"]}.plemiona.pl' not in driver.current_url:
        logged_in = False
        driver.get('https://www.plemiona.pl/page/play/pl' + settings['world_number'])

    driver.find_element_by_id('open_groups').click()
    groups = WebDriverWait(driver, 10, 0.033).until(EC.presence_of_element_located((By.ID, 'group_id'))).get_attribute('innerHTML')
    driver.find_element_by_id('close_groups').click()
    groups = [group[1:-1] for group in re.findall(r'>[^<].+?<', groups)]
    settings['groups'] = groups
    for combobox in args:
        combobox['values'] = settings['groups']
        combobox.set('Wybierz grupę')
        
    if tmp_driver:
        driver.quit()

    if not logged_in:
        driver.get('chrome://newtab')


def cut_time(driver: webdriver) -> None:
    """Finish construction time by using free available speed up"""


def dodge_attacks(driver: webdriver) -> None:
    """Unika wybranej wielkości offów"""    

    villages = player_villages(driver)

    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'incomings_cell'))).click()  # Przełącz do strony nadchodzących ataków
    manage_filters = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a')))  # Filtr ataków
    if driver.find_element_by_xpath('//*[@id="paged_view_content"]/div[2]').get_attribute('style').find('display: none') != -1:  # Czy włączony
        manage_filters.click()  # Włącz filtr ataków
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[2]/td[2]/input'))).clear()  # Etykieta rozkazu
    attack_size = input('1 all\n'
                        '2 small\n'
                        '3 medium\n'
                        '4 big')
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[6]/td/label[{attack_size}]/input'))).click()  # Wielkość idących wojsk
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[7]/td/input'))).click()  # Zapisz i przeładuj
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a')))  # Sprawdź widoczność przycisku "zarządzanie filtrami"
    try:
        driver.find_element_by_id('incomings_table')  # Czy są ataki spełniające powyższe kryteria
    except:
        pass

    targets = driver.find_elements_by_xpath('//*[@id="incomings_table"]/tbody/tr/td[2]/a')
    dates = driver.find_elements_by_xpath('//*[@id="incomings_table"]/tbody/tr/td[6]')

    date_time = time.gmtime()

    targets = [target.get_attribute('href') for target in targets]
    dates = [data.text for data in dates]

    for index, date in enumerate(dates):
        if date.startswith('dzisiaj'):
            dates[index] = date.replace('dzisiaj o', f'{date_time.tm_mday}.{date_time.tm_mon :>02}.{date_time.tm_year}')[:-4]
        elif date.startswith('jutro o'):
            dates[index] = date.replace('jutro o', f'{date_time.tm_mday+1}.{date_time.tm_mon :>02}.{date_time.tm_year}')[:-4]
        else:
            dates[index] = date.replace('dnia ', '').replace('. o', f'.{date_time.tm_year}')[:-4]

    dates = [time.mktime(time.strptime(date, '%d.%m.%Y %H:%M:%S')) for date in dates]
    targets = [target.replace('overview', 'place') for target in targets]

    while True:
        search_for = villages['coords'][villages['id'].index(targets[0][targets[0].find('=')+1:targets[0].find('&')])]
        nearest = sorted([[sqrt(pow(int(search_for[:3])-int(village[:3]), 2) + pow(int(search_for[4:])-int(village[4:]), 2)), index] for index, village in enumerate(villages['coords'])])[1][1]
        targets[0] += '&target=' + villages['id'][nearest]
        while True:        
            if time.time() > dates[0]-5:
                driver.get(targets[0])            
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'selectAllUnits'))).click()
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'target_support'))).click()
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'troop_confirm_go'))).click()
                send_time = time.time() 
                break_attack = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'command-cancel')))
                time.sleep(((dates[0] - send_time) / 2) + 1)
                driver.get(break_attack.get_attribute('href'))
                del dates[0], targets[0]
                break


def gathering_resources(driver: webdriver, settings: dict[str], **kwargs) -> list:
    """Wysyła wojska do zbierania surowców"""

    if 'url_to_gathering' not in kwargs:
        # Tworzy listę docelowo zawierającą słowniki
        list_of_dicts = []

        # Przejście do prawidłowej grupy -> tylko dla posiadaczy konta premium
        if int(settings['account_premium']):
            driver.find_element_by_id('open_groups').click()
            current_group = WebDriverWait(driver, 10, 0.033).until(EC.presence_of_element_located((By.XPATH, '//*[@id="group_id"]/option[@selected="selected"]'))).text

            if current_group != settings['gathering_group']:
                select = Select(driver.find_element_by_id('group_id'))
                select.select_by_visible_text(settings['gathering_group'])
                WebDriverWait(driver, 3, 0.025).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="group_table"]/tbody/tr[1]/td[1]/a'))).click()            
            close_group = WebDriverWait(driver, 3, 0.025).until(EC.element_to_be_clickable((By.ID, 'closelink_group_popup')))
            driver.execute_script('return arguments[0].scrollIntoView(true);', close_group)
            close_group.click()
            WebDriverWait(driver, 2, 0.033).until(EC.presence_of_element_located((By.XPATH, '//*[@id="close_groups"][@style="display: none;"]')))

        # Przejście do ekranu zbieractwa na placu
        url_scavenego = driver.find_element_by_xpath('//*[@id="menu_row2_village"]/a').get_attribute('href')
        url_scavenego = url_scavenego.replace('overview', 'place&mode=scavenge')
        driver.get(url_scavenego)

        # temp od usunięcia po dodatniu wszystkiego w bot_main.py i GUI
        # settings['gathering_troops']['light']['left_in_village'] = 300

        # Początkowa wioska
        starting_village = driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text
    else:
        driver.get(kwargs['url_to_gathering'])

    # Core całej funkcji, kończy gdy przejdzie przez wszystkie wioski
    while True:

        # Dostępne wojska
        available_troops = {}
        doc = lxml.html.fromstring(driver.page_source)
        troops_name = [troop_name.get('name') for troop_name in doc.xpath('//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/input')]
        troops_number = [troop_number.text for troop_number in doc.xpath('//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/a')][:-1]

        # Zapobiega wczytaniu pustego kodu źródłowego - gdy driver.page_source zwróci pusty lub nieaktulny kod HTML
        if not troops_name:
            for _ in range(10):
                time.sleep(0.2)
                doc = lxml.html.fromstring(driver.page_source)
                troops_name = [troop_name.get('name') for troop_name in doc.xpath('//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/input')]
                troops_number = [troop_number.text for troop_number in doc.xpath('//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/a')][:-1]
                if troops_name:
                    break

        for troop_name, troop_number in zip(troops_name, troops_number):
            if int(settings['gathering_troops'][troop_name]['use']) and int(troop_number[1:-1]) > 0:
                available_troops[troop_name] = int(troop_number[1:-1]) - int(settings['gathering_troops'][troop_name]['left_in_village'])
                if available_troops[troop_name] > int(settings['gathering_troops'][troop_name]['send_max']):
                    available_troops[troop_name] = int(settings['gathering_troops'][troop_name]['send_max'])

        # Odblokowane i dostępne poziomy zbieractwa
        troops_to_send = {1: {'capacity': 1}, 2: {'capacity': 0.4}, 3: {'capacity': 0.2}, 4: {'capacity': 4/30}}
        for number, row in enumerate(zip(doc.xpath('//*[@id="scavenge_screen"]/div/div[2]/div/div[3]/div'), (int(settings['gathering']['ommit'][ele]) for ele in settings['gathering']['ommit']))):
            if row[0].get('class')!='inactive-view' or row[1]:
                del troops_to_send[number+1]

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
        sum_capacity = sum(troops_to_send[key]['capacity'] for key in troops_to_send)
        units_capacity = {'spear': 25, 'sword': 15, 'axe': 10, 'archer': 10, 'light': 80, 'marcher': 50, 'heavy': 50, 'knight': 100}
        reduce_ratio = None
        max_resources = int(settings['gathering_max_resources'])        
        round_ups_per_troop = {troop_name: 0 for troop_name in available_troops}
        for key in troops_to_send:
            for troop_name, troop_number in available_troops.items():
                counted_troops_number = troops_to_send[key]['capacity']/sum_capacity*troop_number
                if (counted_troops_number%1)>0.5 and round_ups_per_troop[troop_name]<1:
                    troops_to_send[key][troop_name] = round(counted_troops_number)
                    round_ups_per_troop[troop_name] += 1
                else:
                    troops_to_send[key][troop_name] = int(counted_troops_number)
            if not reduce_ratio:
                sum_troops_capacity = sum([troops_to_send[key][troop_name]*units_capacity[troop_name] if troops_to_send[key][troop_name] > 0 else 0 for troop_name in available_troops]) / 10 / troops_to_send[key]['capacity']
                if sum_troops_capacity > max_resources:
                    reduce_ratio = max_resources / sum_troops_capacity
                else:
                    reduce_ratio = 1
            for troop_name in available_troops:
                if troops_to_send[key][troop_name] > 0:
                    _input = WebDriverWait(driver, 3, 0.01).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/input[@name="{troop_name}"]')))
                    try:
                        _input.click()
                    except:
                        driver.execute_script('return arguments[0].scrollIntoView(false);', _input)
                        _input.click()
                    _input.clear()
                    if reduce_ratio != 1:
                        _input.send_keys(round(troops_to_send[key][troop_name]*reduce_ratio))
                    else:
                        _input.send_keys(troops_to_send[key][troop_name])
            army_sum = 0
            for troop_name in available_troops:
                if troops_to_send[key][troop_name] > 0:
                    match troop_name:
                        case 'light':
                            army_sum += troops_to_send[key]['light'] * 4 * reduce_ratio
                        case 'marcher':
                            army_sum += troops_to_send[key]['marcher'] * 5 * reduce_ratio                        
                        case 'heavy':
                            army_sum += troops_to_send[key]['heavy'] * 6 * reduce_ratio
                        case 'knight':                            
                            army_sum += troops_to_send[key]['knight'] * 10 * reduce_ratio
                        case _:
                            army_sum += troops_to_send[key][troop_name] * reduce_ratio
            if army_sum < 10:
                break
            start = WebDriverWait(driver, 3, 0.01).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="scavenge_screen"]/div/div[2]/div[{key}]/div[3]/div/div[2]/a[1]')))
            driver.execute_script('return arguments[0].scrollIntoView({block: "center"});', start)
            start.click()
            WebDriverWait(driver, 2, 0.025).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="scavenge_screen"]/div/div[2]/div[{key}]/div[3]/div/ul/li[4]/span[@class="return-countdown"]')))

        # tymczasowo w celu zlokalizowania problemu
        # if 'url_to_gathering' in kwargs:
        # logging.error(f'available_troops {available_troops}\ntroops_to_send {troops_to_send}')        
        
        if 'url_to_gathering' in kwargs:

            # Zwraca docelowy url i czas zakończenia zbieractwa w danej wiosce
            doc = lxml.html.fromstring(driver.find_element_by_xpath('//*[@id="scavenge_screen"]/div/div[2]').get_attribute('innerHTML'))
            doc = doc.xpath('//div/div[3]/div/ul/li[4]/span[2]')
            if not [ele.text for ele in doc] and troops_to_send:
                for _ in range(10):
                    time.sleep(0.2)
                    doc = lxml.html.fromstring(driver.find_element_by_xpath('//*[@id="scavenge_screen"]/div/div[2]').get_attribute('innerHTML'))
                    doc = doc.xpath('//div/div[3]/div/ul/li[4]/span[2]')    
                    if [ele.text for ele in doc]:
                        break
            journey_time = [int(_) for _ in max([ele.text for ele in doc]).split(':')]
            journey_time = journey_time[0] * 3600 + journey_time[1] * 60 + journey_time[2]
            return [{'func': 'gathering',
                     'url_to_gathering': driver.current_url, 
                     'start_time': time.time() + journey_time + 2, 
                     'world_number': settings['world_number']}]

        # Tworzy docelowy url i czas zakończenia zbieractwa w danej wiosce
        doc = lxml.html.fromstring(driver.find_element_by_xpath('//*[@id="scavenge_screen"]/div/div[2]').get_attribute('innerHTML'))
        doc = doc.xpath('//div/div[3]/div/ul/li[4]/span[2]')
        try:
            journey_time = [int(_) for _ in max([ele.text for ele in doc]).split(':')]
        except:
            # Pomija wioski z zablokowanym zbieractwem            
            driver.find_element_by_id('ds_body').send_keys('d')
            if starting_village == driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text:
                return list_of_dicts
            continue
        journey_time = journey_time[0] * 3600 + journey_time[1] * 60 + journey_time[2]
        list_of_dicts.append({'func': 'gathering',
                              'url_to_gathering': driver.current_url, 
                              'start_time': time.time() + journey_time + 2, 
                              'world_number': settings['world_number']})

        # Przełącz wioskę i sprawdź czy nie jest to wioska startowa jeśli tak zwróć listę słowników z czasem i linkiem do poszczególnych wiosek
        driver.find_element_by_id('ds_body').send_keys('d')
        if starting_village == driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text:
            return list_of_dicts


def get_villages_id(settings: dict[str], update: bool=False) -> dict:
    """Download, process and save in text file for future use.
    In the end return all villages in the world with proper id.
    """    

    def update_file() -> None:
        """Create or update file with villages and their id's"""

        url = f'http://pl{settings["world_number"]}.plemiona.pl/map/village.txt'
        response = requests.get(url)
        response = response.text
        response = response.splitlines()    
        villages = {}
        for row in response:
            id, _, x, y, _, _, _ = row.split(',')
            villages[x+'|'+y] = id

        try:
            world_villages_file = open(f'villages{settings["world_number"]}.txt', 'w')
        except:
            logging.error(f'There was a problem with villages{settings["world_number"]}.txt')
        else:
            for village_coords, village_id in villages.items():
                world_villages_file.write(f'{village_coords},{village_id}\n')
        finally:
            world_villages_file.close()

    if update:
        update_file()

    villages = {}
    try:
        world_villages_file = open(f'villages{settings["world_number"]}.txt')
    except FileNotFoundError:
        update_file()
        world_villages_file = open(f'villages{settings["world_number"]}.txt')
    else:
        for row in world_villages_file:
            village_coords, village_id = row.split(',')
            villages[village_coords] = village_id
    finally:
        world_villages_file.close()

    return villages


def log_error(driver: webdriver, msg: str='') -> None:
    """Write erros with traceback into log.txt file"""
    
    driver.save_screenshot(f'{time.strftime("%H-%M-%S", time.localtime())}.png')
    error_str = traceback.format_exc()
    error_str = error_str[:error_str.find('Stacktrace')]
    logging.error(f'{time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())}\n'        
                  f'{driver.current_url}\n'
                  f'{error_str}\n'
                  f'{msg}')


def log_in(driver: webdriver, settings: dict) -> bool:
    """Logowanie"""
    
    driver.get('https://www.plemiona.pl/page/play/pl' + settings['world_number'])

    # Czy prawidłowo wczytano i zalogowano się na stronie
    if f'pl{settings["world_number"]}.plemiona.pl' in driver.current_url:
        return True   
    
    # Ręczne logowanie na stronie plemion
    elif 'https://www.plemiona.pl/' == driver.current_url:

        username = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,'input[name="username"]')))
        password = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,'input[name="password"]')))

        username.send_keys(Keys.CONTROL+'a')
        username.send_keys(Keys.DELETE)
        password.send_keys(Keys.CONTROL+'a')
        password.send_keys(Keys.DELETE)
        username.send_keys('klimekop6')
        password.send_keys('u56708')

        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-login'))).click()
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f'//span[text()="Świat {settings["world_number"]}"]'))).click()
        return True   

    # Ponowne wczytanie strony w przypadku nie powodzenia (np. chwilowy brak internetu)
    else: 
        for sleep_time in (5, 15, 60, 120, 300):
            time.sleep(sleep_time)
            driver.get('https://www.plemiona.pl/page/play/pl' + settings['world_number'])
            if f'pl{settings["world_number"]}.plemiona.pl' in driver.current_url:
                return True

    log_error(driver)
    return False


def market_offers(driver: webdriver) -> None:
    """Wystawianie offert tylko dla plemienia"""
    
    current_village_link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="menu_row2_village"]/a')))
    summary_production = current_village_link.get_attribute('href') + '_villages&mode=prod'
    driver.get(summary_production)

    villages_resources = {'villages': [], 'resources': [], 'summary': []}
    villages_resources['villages'] = [village_resources.get_attribute('href').replace('overview', 'market&mode=own_offer') for village_resources in driver.find_elements_by_xpath('//*[@id="production_table"]/tbody/tr/td[2]/span/span/a[1]')]
    resources = [int(resource.text.replace('.', '')) for resource in driver.find_elements_by_xpath('//*[@id="production_table"]/tbody/tr/td[4]/span')]
    villages_resources['resources'] = [[resources[index], resources[index+1], resources[index+2]] for index in range(0, len(resources), 3)] 

    for i in range(3):
        villages_resources['summary'].extend([sum([resource[i] for resource in villages_resources['resources']])]) 
    offer = villages_resources['summary'].index(max(villages_resources['summary']))                 
    need = villages_resources['summary'].index(min(villages_resources['summary']))

    for (village, resource) in zip(villages_resources['villages'], villages_resources['resources']):
        if resource[need]<20000 and resource[offer]>100000:
            driver.get(village)
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="res_buy_selection"]/label[{need+1}]/input'))).click()
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="res_sell_selection"]/label[{offer+1}]/input'))).click()
            how_many = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="own_offer_form"]/table[3]/tbody/tr[2]/td[2]/input')))
            max_to_use = int((resource[offer] - 100000) / 1000) 
            if max_to_use < int(how_many.get_attribute('value')):
                how_many.clear()
                how_many.send_keys(str(max_to_use))      
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="own_offer_form"]/table[3]/tbody/tr[4]/td[2]/label/input')))
            driver.execute_script('return arguments[0].scrollIntoView(true);', element)
            element.click()
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="submit_offer"]')))
            driver.execute_script('return arguments[0].scrollIntoView(true);', element)
            element.click()
        else:
            continue


def mark_villages_on_map(driver: webdriver) -> None:
    """Zaznacza na mapie wioski spełniające konkretne kryteria na podstawie przeglądów plemiennych"""

    villages_to_mark = []
    url = driver.current_url
    village_id = url[url.find('=')+1:url.find('&')]
    url = url[:url.find('?')+1] + 'screen=ally&mode=members_defense&player_id=&village=' + village_id
    player_name = driver.find_element_by_xpath('//*[@id="menu_row"]/td[11]/table/tbody/tr[1]/td/a').get_attribute("innerHTML")
    current_player_id = driver.find_element_by_xpath(f'//*[@id="ally_content"]/div/form/select/option[contains(text(), "{player_name}")]').get_attribute('value')
    player_id = [player_id.get_attribute('value') for player_id in driver.find_elements_by_xpath('//*[@id="ally_content"]/div/form/select/option')][1:]
    del player_id[player_id.index(str(current_player_id))]
    for id in player_id:
        driver.get(url[:url.find('player_id')+10] + id + url[url.rfind('&'):])
        if not driver.find_elements_by_xpath('//*[@id="ally_content"]/div/div'):  # Omija graczy bez wiosek  
            continue
        village_number = len(driver.find_elements_by_xpath('//*[@id="ally_content"]/div/div/table/tbody/tr/td[1]'))
        tmp1 = driver.find_element_by_xpath('//*[@id="ally_content"]/div/div/table/tbody').text
        if tmp1.find('?') != -1:  # Omija graczy którzy nie udostępniają podglądu swoich wojsk
            continue
        tmp1 = [tmp[tmp.find(' w wiosce ')+10:] for tmp in tmp1.splitlines()[1::2]]
        tmp1 = [tmp.split() for tmp in tmp1]
        for index in range(len(tmp1)):
            tmp1[index].insert(0, index*2+2)
        index = 0
        while index < len(tmp1):
            if sum([int(cell) for cell in tmp1[index][1:]]) > 100:
                del tmp1[index]
                continue
            index += 1
        for index in range(len(tmp1)):
            tmp1[index][0] = driver.find_element_by_xpath(f'//*[@id="ally_content"]/div/div/table/tbody/tr[{tmp1[index][0]}]/td[1]/a').get_attribute('href')
        villages_to_mark.extend([to_mark[0] for to_mark in tmp1])

    for village_to_mark in villages_to_mark:
        driver.get(village_to_mark)
        driver.find_element_by_xpath('//*[@id="content_value"]/table/tbody/tr/td[1]/table[2]/tbody/tr[8]').click()  # Otwiera zarządzanie zaznaczeniami mapy
        WebDriverWait(driver, 10, 0.1).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="map_color_assignment"]/form[1]/table/tbody/tr[4]/td/input')))  # Czeka na załadowanie kodu HTML
        groups = [label_name.text for label_name in driver.find_elements_by_xpath('//*[@id="map_group_management"]/table/tbody/tr/td/label')]  # Dostępne grupy zaznaczeń na mapie
        group_name = 'FARMA'  # Nazwa wybranej grupy
        element = driver.find_element_by_xpath(f'//*[@id="map_group_management"]/table/tbody/tr[{groups.index(group_name)+1}]/td/label/input')  # Klika wybraną nazwę grupy
        driver.execute_script('return arguments[0].scrollIntoView(true);', element)
        element.click()
        element = driver.find_element_by_xpath('//*[@id="map_group_management"]/table/tbody/tr/td/input[@value="Zapisz"]')  # Zapisuję wybór
        driver.execute_script('return arguments[0].scrollIntoView(true);', element)
        element.click()


def player_villages(driver: webdriver) -> dict:
    """Tworzy i zwraca słownik z id i koordynatami wiosek gracza"""

    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="menu_row"]/td[11]/a'))).click()
    village_number = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="villages_list"]/thead/tr/th[1]'))).text
    village_number = int(village_number[village_number.find('(')+1:-1])
    if village_number > 100:
        element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="villages_list"]/tbody/tr[101]/td/a')))
        driver.execute_script('return arguments[0].scrollIntoView(true);', element)
        element.click()
        WebDriverWait(driver, 10, 0.1).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="villages_list"]/tbody/tr[101]/td[3]')))

    villages = {'id': [id.get_attribute('data-id') for id in driver.find_elements_by_xpath('//*[@id="villages_list"]/tbody/tr/td[1]/table/tbody/tr/td[1]/span')],
                'coords': [coords.text for coords in driver.find_elements_by_xpath('//*[@id="villages_list"]/tbody/tr/td[3]')]}

    return villages


def premium_exchange(driver: webdriver, settings: dict) -> None:
    """Umożliwia automatyczną sprzedaż lub zakup surwców za punkty premium"""
    
    url = driver.current_url
    if 'intro' in url or 'php?screen' in url:  # Jeśli na stronie startowej zaraz po zalogowaniu
        url = driver.find_element_by_xpath('//*[@id="menu_row2_village"]/a')
        url = url.get_attribute('href')
        url = url[:url.find('&screen=')+8] + 'market&mode=exchange'
        driver.get(url)
    else:
        url = url[:url.find('&screen=')+8] + 'market&mode=exchange'
        driver.get(url)

    starting_village = driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text

    while True:

        if driver.find_elements_by_xpath('//*[@id="village_switch_left"]'):
            coords = driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text
            coords = re.search(r'\d{3}\|\d{3}', coords).group()
            if coords in settings['market']['market_exclude_villages']:
                driver.find_element_by_id('ds_body').send_keys('d')
            if starting_village == driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text:
                return

        chat = driver.find_element_by_xpath('//*[@id="chat-wrapper"]')
        driver.execute_script("arguments[0].innerHTML = '';", chat)

        resources_doc = lxml.html.fromstring(driver.find_element_by_xpath('//*[@id="header_info"]/tbody/tr/td[4]/table/tbody/tr[1]/td/table/tbody/tr').get_attribute('innerHTML'))
        resources_name = ('wood', 'stone', 'iron')
        resources_available = {}
        for resource in resources_name:
            resources_available[resource] = int(resources_doc.get_element_by_id(resource).text)

        exchange_doc = lxml.html.fromstring(driver.find_element_by_xpath('//*[@id="premium_exchange_form"]/table/tbody').get_attribute('innerHTML'))
        exchange_resources = {resource_name: {'current_resource_rate': 0, 'max_exchange_resource_can_receive': 0} for resource_name in resources_name}
        for resource in resources_name:
            resource_capacity = exchange_doc.get_element_by_id(f'premium_exchange_capacity_{resource}').text
            resource_stock = exchange_doc.get_element_by_id(f'premium_exchange_stock_{resource}').text
            exchange_resources[resource]['max_exchange_resource_can_receive'] = int(resource_capacity) - int(resource_stock)
            resource_rate = int(driver.find_element_by_xpath(f'//*[@id="premium_exchange_rate_{resource}"]/div[1]').text)
            exchange_resources[resource]['current_resource_rate'] = int(resource_rate)
        if all(not exchange_resources[resource_name]['max_exchange_resource_can_receive'] for resource_name in exchange_resources):
            return
        SUM_EXCHANGE_RATE = sum(resource['current_resource_rate'] for resource in exchange_resources.values())    
        
        market_history_file = open(f'market_history_{settings["world_number"]}.txt', 'a')
        market_history_file.write(f'{time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())} ')
        market_history_file.writelines(f'{resource_name} {value["current_resource_rate"]} ' for resource_name, value in exchange_resources.items())            
        market_history_file.write('\n')
        market_history_file.close()

        STARTING_TRANSPORT_CAPACITY = int(driver.find_element_by_xpath('//*[@id="market_merchant_max_transport"]').text)
        transport_capacity = STARTING_TRANSPORT_CAPACITY
        if not transport_capacity:
            if driver.find_elements_by_xpath('//*[@id="village_switch_left"]'):
                driver.find_element_by_id('ds_body').send_keys('d')
                if starting_village == driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text:
                    return
                continue
            else:
                return
        
        exchange_resources = dict(sorted(exchange_resources.items(), key=lambda item: item[1]['current_resource_rate']))

        min_exchange_rate = min(resource['current_resource_rate'] for resource in exchange_resources.values())
        max_exchange_rate = max(resource['current_resource_rate'] for resource in exchange_resources.values())
        for resource_name in exchange_resources:
            max_resource_to_sell = exchange_resources[resource_name]['max_exchange_resource_can_receive']
            exchange_rate = exchange_resources[resource_name]['current_resource_rate']

            if max_resource_to_sell and transport_capacity>=1000 and transport_capacity>exchange_rate:
                resource_to_sell = min((max_resource_to_sell, transport_capacity, resources_available[resource_name]))

                current_exchange_rate = int(driver.find_element_by_xpath(f'//*[@id="premium_exchange_rate_{resource_name}"]/div[1]').text)       
                if (current_exchange_rate > int(settings['market'][resource_name]['max_exchange_rate'])  # Pomiń jeśli kurs jest powyżej ustalonej wartości
                        or current_exchange_rate >= resources_available[resource_name]):  # Pomiń jeśli kurs jest wyższy od dostępnych surowców
                    continue

                if exchange_rate == min_exchange_rate:
                    if resource_to_sell > round(max_exchange_rate/SUM_EXCHANGE_RATE*STARTING_TRANSPORT_CAPACITY):
                        resource_to_sell = round(max_exchange_rate/SUM_EXCHANGE_RATE*STARTING_TRANSPORT_CAPACITY)
                elif exchange_rate == max_exchange_rate:
                    if resource_to_sell > round(min_exchange_rate/SUM_EXCHANGE_RATE*STARTING_TRANSPORT_CAPACITY):                    
                        resource_to_sell = round(min_exchange_rate/SUM_EXCHANGE_RATE*STARTING_TRANSPORT_CAPACITY)
                else:
                    if resource_to_sell > round(exchange_rate/SUM_EXCHANGE_RATE*STARTING_TRANSPORT_CAPACITY):
                        resource_to_sell = round(exchange_rate/SUM_EXCHANGE_RATE*STARTING_TRANSPORT_CAPACITY)
                resource_to_sell -= current_exchange_rate
                if resource_to_sell < 1:
                    resource_to_sell = 1

                input = driver.find_element_by_xpath(f'//*[@id="premium_exchange_sell_{resource_name}"]/div[1]/input')
                input.send_keys(f'{resource_to_sell}')
                input.send_keys(Keys.ENTER)

                try:
                    final_resource_amount_to_sell = WebDriverWait(driver, 5, 0.025).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="confirmation-msg"]/div/table/tbody/tr[2]/td[2]')))
                except TimeoutException:
                    driver.find_element_by_xpath('//*[@id="premium_exchange_form"]/input').click()
                    final_resource_amount_to_sell = WebDriverWait(driver, 5, 0.025).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="confirmation-msg"]/div/table/tbody/tr[2]/td[2]')))
                final_resource_amount_to_sell = final_resource_amount_to_sell.text
                final_resource_amount_to_sell = int(re.search(r'\d+', final_resource_amount_to_sell).group())

                if final_resource_amount_to_sell > resources_available[resource_name]:
                    current_exchange_rate = driver.find_element_by_xpath('//*[@id="confirmation-msg"]/div/p[2]').text
                    current_exchange_rate = ceil(final_resource_amount_to_sell/int(re.search(r'\d+', current_exchange_rate).group()))
                    
                    driver.find_element_by_xpath('//*[@id="premium_exchange"]/div/div/div[2]/button[2]').click()
                    
                    input.clear()
                    input.send_keys(f'{resources_available[resource_name]-current_exchange_rate}')
                    input.send_keys(Keys.ENTER)

                transport_capacity -= ceil((final_resource_amount_to_sell/1000)*1000)

                WebDriverWait(driver, 5, 0.025).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="premium_exchange"]/div/div/div[2]/button[1]'))).click()
                time.sleep(4)
        
        if driver.find_elements_by_xpath('//*[@id="village_switch_left"]'):
            driver.find_element_by_id('ds_body').send_keys('d')
            if starting_village == driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text:
                return
        else:
            return


def send_back_support(driver: webdriver) -> None:
    """Odsyłanie wybranego wsparcia z przeglądanej wioski"""

    code = driver.find_element_by_xpath('//*[@id="withdraw_selected_units_village_info"]/table/tbody').get_attribute("innerHTML")
    temp = code.split('<tr>')[2:-1]
    omit = 2
    for index in range(len(temp)):
        temp[index] = temp[index].split('<td style')[1:-5]
        if temp[index][0].find('has-input') == -1:
            continue
        del temp[index][4], temp[index][2]
        for row, value in zip(range(len(temp[index])), (2, 3, 5, 7)):
            temp[index][row] = [value, temp[index][row]]
        for row in range(len(temp[index])):
            if temp[index][row][0] == omit:
                continue
            if temp[index][row][1].find('hidden') != -1:
                continue
            ele = driver.find_element_by_xpath(f'//*[@id="withdraw_selected_units_village_info"]/table/tbody/tr[{index+2}]/td[{temp[index][row][0]}]')
            html = temp[index][row][1][temp[index][row][1].find('<'):-5]
            html = html[:html.find('value')] + 'value="" ' + html[html.find('min'):]
            driver.execute_script(f'''arguments[0].innerHTML = '{html}';''', ele)


def send_troops(driver: webdriver, settings: dict) -> int:
    """Send troops at given time.
    It can be attack or help.
    You can also use it for fakes.
    """

    send_time = settings['scheduler']['ready_schedule'][0]['send_time']
    list_to_send = []
    for cell_in_list in settings['scheduler']['ready_schedule']:
        if cell_in_list['send_time'] > send_time+8: 
            break
        list_to_send.append(cell_in_list)

    attacks_list_to_repeat = []
    for index, send_info in enumerate(list_to_send):  

        if index > 0:
            driver.execute_script(f'window.open("{send_info["url"]}");')
            driver.switch_to.window(driver.window_handles[index])
        else:
            driver.get(send_info['url'])

        match send_info['template_type']:
            case 'send_all':

                def choose_all_units_with_exceptions(troops_dict: dict) -> None:
                    '''Choose all units and than unclick all unnecessary'''

                    slowest_troop_speed = troops_dict[send_info['slowest_troop']]
                    for troop_name, troop_speed in troops_dict.items():
                        if troop_speed > slowest_troop_speed:
                            del troops_dict[troop_name]

                    driver.find_element(By.ID, 'selectAllUnits').click()
                    doc = lxml.html.fromstring(driver.find_element(By.XPATH, '//*[@id="command-data-form"]/table/tbody/tr').get_attribute('innerHTML'))
                    for col in doc:
                        col = col.xpath('table/tbody/tr/td')
                        for troop in col:
                            if troop.get('class') == 'nowrap unit-input-faded':
                                continue
                            troop_name = troop.xpath('a')[1].get('data-unit')
                            if troop_name not in troops_dict:
                                troop_button_id = troop.xpath('a')[1].get('id')
                                driver.find_element(By.ID, troop_button_id).click()

                # Choose troops to send
                match send_info['army_type']:
                    
                    case 'only_off':
                        troops_off = {
                            'axe': 18,
                            'light': 10,
                            'marcher': 10,
                            'ram': 30,
                            'catapult': 30,
                            'knight': 10,
                            'snob': 35
                        }
                        choose_all_units_with_exceptions(troops_dict=troops_off)
                        
                    case 'only_deff':
                        troops_deff = {
                            'spear': 18,
                            'sword': 22,
                            'archer': 18,
                            'spy': 9,
                            'heavy': 11,
                        }
                        choose_all_units_with_exceptions(troops_dict=troops_deff)

                if send_info['send_snob'] == 'send_snob':
                    if send_info['snob_amount'] and send_info['snob_amount']!='0':
                        snob_input = driver.find_element(By.ID, 'unit_input_snob')
                        snob_input.clear()
                        snob_input.send_keys('1')

            case 'send_fake':
                # Choose troops to send

                pass
            case 'send_my_template':
                # Choose troops to send
                for troop_name, troop_value in send_info['troops'].items():
                    if troop_value:
                        troop_input = driver.find_element(By.ID, f'unit_input_{troop_name}')
                        troop_input.send_keys(troop_value)

                if send_info['repeat_attack'] and int(send_info['repeat_attack']):
                    if send_info['repeat_attack_number']:                        
                        repeat_attack_number = int(send_info['repeat_attack_number'])
                        if repeat_attack_number > 0:
                            # Add dict to list of attacks to repeat and in the end add to self.to_do
                            attacks_list_to_repeat.append(
                                {
                                    'func': 'send_troops', 
                                    'start_time': send_info['send_time'] + 2*send_info['travel_time'] + 1, 
                                    'world_number': settings['world_number']}
                                )
                            # Add the same attack to scheduler with changed send_time etc.
                            attack_to_add = send_info.copy()
                            if repeat_attack_number == 1:
                                attack_to_add['repeat_attack'] = 0
                            attack_to_add['repeat_attack_number'] = repeat_attack_number-1
                            attack_to_add['send_time'] += 2*send_info['travel_time'] + 9
                            arrival_time_in_sec = attack_to_add['send_time'] + send_info['travel_time']
                            arrival_time = time.localtime(arrival_time_in_sec)
                            attack_to_add['arrival_time'] = time.strftime(f'%d.%m.%Y %H:%M:%S:{round(random.random()*100000):0<6}', arrival_time)
                            settings['scheduler']['ready_schedule'].append(attack_to_add)
        
        # Click command_type button (attack or support)
        driver.find_element(By.ID, send_info['command']).click()    

    # Sort all added attacks in scheduler
    if attacks_list_to_repeat:
        settings['scheduler']['ready_schedule'].sort(key=lambda x: x['send_time'])             

    if len(list_to_send) > 1:
        driver.switch_to.window(driver.window_handles[0])
        def click_without_wait(ele):
            try:
                ele.click()
            except:
                pass

    for index, send_info in enumerate(list_to_send):

        if index > 0:
            driver.switch_to.window(driver.window_handles[1])

        current_time = driver.find_element(By.XPATH, '//*[@id="date_arrival"]/span')  # 01
        send_button = driver.find_element(By.ID, 'troop_confirm_submit')
        arrival_time = re.search(r'\d{2}:\d{2}:\d{2}', send_info['arrival_time']).group()

        if current_time.text[-8:] < arrival_time:   
            ms = int(send_info['arrival_time'][-3:]) - 15
            if ms < 10:
                sec = 0
            else:
                sec = ms / 1000
            while True:
                if current_time.text[-8:] == arrival_time:
                    if sec:
                        time.sleep(sec)
                    if len(list_to_send) == 1:
                        send_button.click()
                    else:
                        threading.Thread(
                            target=lambda: click_without_wait(send_button), 
                            name='fast_click', 
                            daemon=True
                            ).start()        
                    break
        else:
            if len(list_to_send) == 1:
                send_button.click()
            else:
                threading.Thread(
                    target=lambda: click_without_wait(send_button), 
                    name='fast_click', 
                    daemon=True
                    ).start()

    if len(list_to_send) > 1:
        time.sleep(0.5)            
        for index in range(len(list_to_send)):
            if index > 0:
                driver.switch_to.window(driver.window_handles[1])
                driver.close()
        driver.switch_to.window(driver.window_handles[0])
        
    return len(list_to_send), attacks_list_to_repeat

def train_knight(driver: webdriver) -> None:
    """Train knights to gain experience and lvl up"""


def unwanted_page_content(driver: webdriver, html: str) -> bool:
    """Deal with error made by popup boxes like daily bonus, tribe quests, captcha etc."""

    if html.find('captcha') != -1:
        driver.save_screenshot('before.png')
        time.sleep(35)
        driver.save_screenshot('after.png')
        return True

    # Bonus dzienny i pozostałe okna należacę do popup_box_container
    elif html.find('popup_box_container') != -1:
        # Poczekaj do 2 sekund w celu wczytania całości dynamicznego kontentu       
        for _ in range(25):
            time.sleep(0.1)
            html = driver.page_source
            if html.find('popup_box_daily_bonus') != -1:
                break
        
        # Odbierz bonus dzienny
        if html.find('popup_box_daily_bonus') != -1:

            def open_daily_bonus() -> bool:
                try:
                    popup_box_html = WebDriverWait(driver, 5, 0.25).until(EC.element_to_be_clickable((By.ID, 'popup_box_daily_bonus'))).get_attribute('innerHTML')
                    bonus = WebDriverWait(driver, 2, 0.25).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="daily_bonus_content"]/div/div/div/div/div[@class="db-chest unlocked"]/../div[3]/a')))
                    driver.execute_script('return arguments[0].scrollIntoView(true);', bonus)
                    bonus.click()
                            
                    if popup_box_html.find('icon header premium') != -1:
                        WebDriverWait(driver, 2, 0.25).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="popup_box_daily_bonus"]/div/a'))).click()
                    
                    for _ in range(50):
                        try:
                            driver.find_element_by_id('popup_box_daily_bonus')
                            time.sleep(0.05)
                        except:
                            break
                    return True                    
                except BaseException:                    
                    return False

            # Próbuję odebrać bonus dzienny jeśli się nie uda odświeża stronę i próbuję ponownie. W razie niepowodzenia tworzy log błędu
            try:
                if open_daily_bonus():
                    return True
                else:
                    driver.refresh()
                    if open_daily_bonus():
                        return True
                    else:
                        raise
            except BaseException:                 
                logging.error(f'{time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())} {traceback.format_exc()}')
                return False

        # Zamknij wszystkie popup_boxy które nie dotyczą bonusu dziennego
        else:
            driver.find_element_by_xpath('//*[@id="ds_body"]/div[@class="popup_box_container"]/div/div/a').click()
            for _ in range(30):
                try:
                    driver.find_element_by_xpath('//*[@id="ds_body"]/div[@class="popup_box_container"]')
                    time.sleep(0.05)
                except:
                    break
            return True

    # Zamyka otwarte okno grup    
    elif driver.find_elements_by_xpath('//*[@id="open_groups"][@style="display: none;"]'):
        close_group = driver.find_element_by_id('closelink_group_popup')
        driver.execute_script('return arguments[0].scrollIntoView(true);', close_group)
        close_group.click()
        
        return True

    # Nieznane -> log_error
    else:
        log_error(driver)
        return False