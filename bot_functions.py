from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import Select
from math import sqrt
from lxml import html
import time
import re
import traceback

import logging
logging.basicConfig(filename='log.txt', level=logging.ERROR)

def log_error(driver: webdriver) -> None:
    """ write erros with traceback into log.txt file """

    driver.save_screenshot(f'{time.strftime("%H-%M-%S", time.localtime())}.png')
    logging.error(f'{time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())} \n{driver.current_url}\n {traceback.format_exc()}')

def log_in(driver: webdriver, settings: dict) -> bool:
    """ logowanie """
    
    driver.get('https://www.plemiona.pl/page/play/pl' + settings['world_number'])

    # czy prawidłowo wczytano i zalogowano się na stronie
    if f'pl{settings["world_number"]}.plemiona.pl' in driver.current_url:
        return True   

    # ręczne logowanie na stronie plemion
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

    # ponowne wczytanie strony w przypadku nie powodzenia (np. chwilowy brak internetu)
    else: 
        for sleep_time in (5, 15, 60, 120, 300):
            time.sleep(sleep_time)
            driver.get('https://www.plemiona.pl/page/play/pl' + settings['world_number'])
            if f'pl{settings["world_number"]}.plemiona.pl' in driver.current_url:
                return True

    log_error(driver)
    return False

def attacks_labels(driver: webdriver) -> bool:
    """ etykiety ataków """

    if not driver.find_element_by_id('incomings_amount').text:
        return False
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'incomings_cell'))).click() # otwarcie karty z nadchodzącymi atakami
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[1]/*[@data-group-type="all"]'))).click() # zmiana grupy na wszystkie
    manage_filters = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a'))) # zwraca element z filtrem ataków
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
    return True

def dodge_attacks(driver: webdriver) -> None:
    """ unika wybranej wielkości offów """    

    villages = player_villages(driver)

    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'incomings_cell'))).click() # przełącz do strony nadchodzących ataków
    manage_filters = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a'))) # filtr ataków
    if driver.find_element_by_xpath('//*[@id="paged_view_content"]/div[2]').get_attribute('style').find('display: none') != -1: # czy włączony
        manage_filters.click() # włącz filtr ataków
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[2]/td[2]/input'))).clear() # etykieta rozkazu
    attack_size = input('1 all\n'
                        '2 small\n'
                        '3 medium\n'
                        '4 big')
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[6]/td/label[{attack_size}]/input'))).click() # wielkość idących wojsk
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[7]/td/input'))).click() # zapisz i przeładuj
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a'))) # sprawdź widoczność przycisku "zarządzanie filtrami"
    try:
        driver.find_element_by_id('incomings_table') # czy są ataki spełniające powyższe kryteria
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
            if time.time() > dates[0] - 5:
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

def player_villages(driver: webdriver) -> dict:
    """ tworzy i zwraca słownik z id i koordynatami wiosek gracza """

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

def market_offers(driver: webdriver) -> None:
    """ wystawianie offert tylko dla plemienia """
    
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
        if resource[need] < 20000 and resource[offer] > 100000:
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

def send_back_support(driver: webdriver) -> None:
    """ odsyłanie wybranego wsparcia z przeglądanej wioski """

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
            
def mark_villages_on_map(driver: webdriver) -> None:
    """ zaznacza na mapie wioski spełniające konkretne kryteria na podstawie przeglądów plemiennych """

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
        if not driver.find_elements_by_xpath('//*[@id="ally_content"]/div/div'): # omija graczy bez wiosek  
            continue
        village_number = len(driver.find_elements_by_xpath('//*[@id="ally_content"]/div/div/table/tbody/tr/td[1]'))
        tmp1 = driver.find_element_by_xpath('//*[@id="ally_content"]/div/div/table/tbody').text
        if tmp1.find('?') != -1: # omija graczy którzy nie udostępniają podglądu swoich wojsk
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
        driver.find_element_by_xpath('//*[@id="content_value"]/table/tbody/tr/td[1]/table[2]/tbody/tr[8]').click() # otwiera zarządzanie zaznaczeniami mapy
        WebDriverWait(driver, 10, 0.1).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="map_color_assignment"]/form[1]/table/tbody/tr[4]/td/input'))) # czeka na załadowanie kodu HTML
        groups = [label_name.text for label_name in driver.find_elements_by_xpath('//*[@id="map_group_management"]/table/tbody/tr/td/label')] # dostępne grupy zaznaczeń na mapie
        group_name = 'FARMA' # nazwa wybranej grupy
        element = driver.find_element_by_xpath(f'//*[@id="map_group_management"]/table/tbody/tr[{groups.index(group_name)+1}]/td/label/input') # klika wybraną nazwę grupy
        driver.execute_script('return arguments[0].scrollIntoView(true);', element)
        element.click()
        element = driver.find_element_by_xpath('//*[@id="map_group_management"]/table/tbody/tr/td/input[@value="Zapisz"]') # zapisuję wybór
        driver.execute_script('return arguments[0].scrollIntoView(true);', element)
        element.click()

def auto_farm(driver: webdriver, settings: dict[str]) -> None:
    """ automatyczne wysyłanie wojsk w asystencie farmera """ 

    # przechodzi do asystenta farmera
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'manager_icon_farm'))).click()

    # sprawdza czy znajduję się w prawidłowej grupie jeśli nie to przechodzi do prawidłowej -> tylko dla posiadaczy konta premium
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

    # początkowa wioska - format '(439|430) K44'
    starting_village = driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text

    while True:
        
        # szablon A i B plus aktualnie dostępne jednostki w wiosce
        template_troops = driver.find_element_by_id('content_value').get_attribute('innerHTML')
        template_troops = template_troops[template_troops.find('<table class="vis"'):template_troops.find('<script type="text/javascript">')]
        available_troops = template_troops[template_troops.find('id="units_home"'):].split('<tr>')[2:]
        template_troops = {'A': template_troops[:template_troops.find('</tbody>')],'B': template_troops[template_troops.find('farm_icon_b'):template_troops.find('id="farm_units"')]}
        template_troops['A'] = template_troops['A'].split('<tr>')[2:]
        template_troops['B'] = template_troops['B'].split('<tr>')[1:]
        template_troops['A'] = template_troops['A'][0].split('<td')[1:-1]
        template_troops['B'] = template_troops['B'][0].split('<td')[1:-1]

        for key in template_troops:
            tmp = {}
            for row in template_troops[key]:
                value = int(row[row.find('value="')+7:row.rfind('">')])
                if value:
                    tmp[row[row.find('name="')+6:row.find('size')-2]] = value
            template_troops[key] = tmp

        for row in available_troops:
            available_troops = row.split('<td')[2:]
        for index, row in enumerate(available_troops): 
            available_troops[index] = {'key': row[row.find('id="')+4:row.find('">')], 'value': row[row.find('">')+2:row.find('</td')]}

        tmp = available_troops
        available_troops = {}
        for row in tmp:
            available_troops[row['key']] = int(row['value'])

        # pomija wioskę jeśli nie ma z niej nic do wysłania
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

        # lista poziomów murów
        walls_level = driver.find_element_by_id('plunder_list').get_attribute('innerHTML').split('<tr')[3:]
        for index, row in enumerate(walls_level):
            walls_level[index] = row.split('<td')[7:8]
        for index, row in enumerate(walls_level):
            for ele in row:
                walls_level[index] = ele[ele.find('>')+1:ele.find('<')] 
        walls_level = [ele if ele=='?' else int(ele) for ele in walls_level]
        
        # lista przycisków do wysyłki szablonów A, B i C
        villages_to_farm = {}
            
        if int(settings['A']['active']): 
            villages_to_farm['A'] = 9 # szablon A
        if int(settings['B']['active']): 
            villages_to_farm['B'] = 10 # szablon B
        if int(settings['C']['active']):     
            villages_to_farm['C'] = 11 # szablon C

        # wysyłka wojsk w asystencie farmera
        start_time = 0
        no_units = False        
        for index, template in enumerate(villages_to_farm):

            if skip[template]:
                continue

            # ukrywa chat
            chat = driver.find_element_by_xpath('//*[@id="chat-wrapper"]')
            driver.execute_script("arguments[0].innerHTML = '';", chat)

            villages_to_farm[template] = driver.find_elements_by_xpath(f'//*[@id="plunder_list"]/tbody/tr/td[{villages_to_farm[template]}]/a')
            captcha_solved = False
            for village, wall_level in zip(villages_to_farm[template], walls_level): 
                if isinstance(wall_level, str) and not int(settings[template]['wall_ignore']):
                    continue        
                if int(settings[template]['wall_ignore']) or int(settings[template]['min_wall']) <= wall_level <= int(settings[template]['max_wall']):
                    for unit, number in template_troops[template].items():
                        if available_troops[unit] - number < 0:
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
                    while time.time() - start_time < 0.195:
                        time.sleep(0.01)
                    driver.execute_script('return arguments[0].scrollIntoView(true);', village)
                    village.click()
                start_time = time.time()
            if index < len(villages_to_farm)-1:
                no_units = False
                driver.refresh()

        # przełącz wioskę i sprawdź czy nie jest to wioska startowa
        ActionChains(driver).send_keys('d').perform()
        if starting_village == driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text:
            break

def check_groups(driver: webdriver, settings: dict[str], run_driver, *args) -> None:
    """ sprawdza dostępne grupy i zapisuje je w settings.json """
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

def gathering_resources(driver: webdriver, settings: dict[str], **kwargs) -> list:
    """ wysyła wojska do zbierania surowców """

    if 'url_to_gathering' not in kwargs:
        # tworzy listę docelowo zawierającą słowniki
        list_of_dicts = []

        # przejście do prawidłowej grupy -> tylko dla posiadaczy konta premium
        if int(settings['account_premium']):
            driver.find_element_by_id('open_groups').click()
            current_group = WebDriverWait(driver, 10, 0.033).until(EC.presence_of_element_located((By.XPATH, '//*[@id="group_id"]/option[@selected="selected"]'))).text

            if current_group != settings['gathering_group']:
                select = Select(driver.find_element_by_id('group_id'))
                select.select_by_visible_text(settings['gathering_group'])
                WebDriverWait(driver, 10, 0.033).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="group_table"]/tbody/tr[1]/td[1]/a'))).click()
            close_group = driver.find_element_by_id('closelink_group_popup')
            driver.execute_script('return arguments[0].scrollIntoView(true);', close_group)
            close_group.click()
            WebDriverWait(driver, 2, 0.033).until(EC.presence_of_element_located((By.XPATH, '//*[@id="close_groups"][@style="display: none;"]')))

        # przejście do ekranu zbieractwa na placu
        url_scavenego = driver.find_element_by_xpath('//*[@id="menu_row2_village"]/a').get_attribute('href')
        url_scavenego = url_scavenego.replace('overview', 'place&mode=scavenge')
        driver.get(url_scavenego)

        # temp od usunięcia po dodatniu wszystkiego w bot_main.py i GUI
        # settings['gathering_troops']['light']['left_in_village'] = 300

        # początkowa wioska
        starting_village = driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text
    else:
        driver.get(kwargs['url_to_gathering'])

    # core całej funkcji, kończy gdy przejdzie przez wszystkie wioski
    while True:

        # dostępne wojska
        available_troops = {}
        doc = html.fromstring(driver.page_source)
        troops_name = [troop_name.get('name') for troop_name in doc.xpath('//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/input')]
        troops_number = [troop_number.text for troop_number in doc.xpath('//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/a')][:-1]

        # zapobiega wczytaniu pustego kodu źródłowego - gdy driver.page_source zwróci pusty lub nieaktulny kod HTML
        if not troops_name:
            for _ in range(10):
                time.sleep(0.2)
                doc = html.fromstring(driver.page_source)
                troops_name = [troop_name.get('name') for troop_name in doc.xpath('//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/input')]
                troops_number = [troop_number.text for troop_number in doc.xpath('//*[@id="scavenge_screen"]/div/div[1]/table/tbody/tr[2]/td/a')][:-1]
                if troops_name:
                    break

        for troop_name, troop_number in zip(troops_name, troops_number):
            if int(settings['gathering_troops'][troop_name]['use']) and int(troop_number[1:-1]) > 0:
                available_troops[troop_name] = int(troop_number[1:-1]) - int(settings['gathering_troops'][troop_name]['left_in_village'])

        # odblokowane i dostępne poziomy zbieractwa
        troops_to_send = {1: {'capacity': 1}, 2: {'capacity': 0.4}, 3: {'capacity': 0.2}, 4: {'capacity': 4/30}}
        for number, row in enumerate(zip(doc.xpath('//*[@id="scavenge_screen"]/div/div[2]/div/div[3]/div'), (int(settings['gathering']['ommit'][ele]) for ele in settings['gathering']['ommit']))):
            if row[0].get('class') != 'inactive-view' or row[1]:
                del troops_to_send[number+1]

        # ukrywa chat
        chat = driver.find_element_by_xpath('//*[@id="chat-wrapper"]')
        driver.execute_script("arguments[0].innerHTML = '';", chat)

        # obliczenie i wysyłanie wojsk na zbieractwo
        sum_capacity = sum(troops_to_send[key]['capacity'] for key in troops_to_send)
        units_capacity = {'spear': 25, 'sword': 15, 'axe': 10, 'archer': 10, 'light': 80, 'marcher': 50, 'heavy': 50, 'knight': 100}
        reduce_ratio = None
        max_resources = int(settings['gathering_max_resources'])        
        round_ups_per_troop = {troop_name: 0 for troop_name in available_troops}
        for key in troops_to_send:
            for troop_name, troop_number in available_troops.items():
                counted_troops_number = troops_to_send[key]['capacity']/sum_capacity*troop_number
                if (counted_troops_number % 1) > 0.5 and round_ups_per_troop[troop_name] < 1:
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
                    _input.click()
                    try:
                        _input.is_selected
                    except:
                        driver.execute_script('return arguments[0].scrollIntoView(true);', _input)
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
            driver.execute_script('return arguments[0].scrollIntoView(true);', start)
            start.click()
            WebDriverWait(driver, 2, 0.025).until(EC.element_to_be_clickable((By.XPATH, f'//*[@id="scavenge_screen"]/div/div[2]/div[{key}]/div[3]/div/ul/li[4]/span[@class="return-countdown"]')))

        # tymczasowo w celu zlokalizowania problemu
        # if 'url_to_gathering' in kwargs:
        # logging.error(f'available_troops {available_troops}\ntroops_to_send {troops_to_send}')        
        
        if 'url_to_gathering' in kwargs:

            # zwraca docelowy url i czas zakończenia zbieractwa w danej wiosce
            doc = html.fromstring(driver.find_element_by_xpath('//*[@id="scavenge_screen"]/div/div[2]').get_attribute('innerHTML'))
            doc = doc.xpath('//div/div[3]/div/ul/li[4]/span[2]')
            if not [ele.text for ele in doc] and troops_to_send:
                for _ in range(10):
                    time.sleep(0.2)
                    doc = html.fromstring(driver.find_element_by_xpath('//*[@id="scavenge_screen"]/div/div[2]').get_attribute('innerHTML'))
                    doc = doc.xpath('//div/div[3]/div/ul/li[4]/span[2]')    
                    if [ele.text for ele in doc]:
                        break
            journey_time = [int(_) for _ in max([ele.text for ele in doc]).split(':')]
            journey_time = journey_time[0] * 3600 + journey_time[1] * 60 + journey_time[2]
            return [{'func': 'gathering',
                     'url_to_gathering': driver.current_url, 
                     'start_time': time.time() + journey_time + 1, 
                     'world_number': settings['world_number']}]

        # tworzy docelowy url i czas zakończenia zbieractwa w danej wiosce
        doc = html.fromstring(driver.find_element_by_xpath('//*[@id="scavenge_screen"]/div/div[2]').get_attribute('innerHTML'))
        doc = doc.xpath('//div/div[3]/div/ul/li[4]/span[2]')
        try:
            journey_time = [int(_) for _ in max([ele.text for ele in doc]).split(':')]
        except:
            # pomija wioski z zablokowanym zbieractwem            
            driver.find_element_by_id('ds_body').send_keys('d')
            if starting_village == driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text:
                return list_of_dicts
            continue
        journey_time = journey_time[0] * 3600 + journey_time[1] * 60 + journey_time[2]
        list_of_dicts.append({'func': 'gathering',
                              'url_to_gathering': driver.current_url, 
                              'start_time': time.time() + journey_time + 1, 
                              'world_number': settings['world_number']})

        # przełącz wioskę i sprawdź czy nie jest to wioska startowa jeśli tak zwróć listę słowników z czasem i linkiem do poszczególnych wiosek
        driver.find_element_by_id('ds_body').send_keys('d')
        if starting_village == driver.find_element_by_xpath('//*[@id="menu_row2"]/td/b').text:
            return list_of_dicts

def unwanted_page_content(driver: webdriver, html: str) -> bool:
    """ deal with error made by popup boxes like daily bonus, tribe quests, captcha etc. """

    if html.find('captcha') != -1:
        driver.save_screenshot('before.png')
        time.sleep(30)
        driver.save_screenshot('after.png')
        return True

    # bonus dzienny i pozostałe okna należacę do popup_box_container
    elif html.find('popup_box_container') != -1:
        # poczekaj do 2 sekund w celu wczytania całości dynamicznego kontentu       
        for _ in range(25):
            time.sleep(0.1)
            html = driver.page_source
            if html.find('popup_box_daily_bonus') != -1:
                break
        
        # odbierz bonus dzienny
        if html.find('popup_box_daily_bonus') != -1:        
            try:
                popup_box_html = WebDriverWait(driver, 5, 0.25).until(EC.element_to_be_clickable((By.ID, 'popup_box_daily_bonus'))).get_attribute('innerHTML')
                bonus = WebDriverWait(driver, 2, 0.25).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="daily_bonus_content"]/div/div/div/div/div[@class="db-chest unlocked"]/../div[3]/a')))
                driver.execute_script('return arguments[0].scrollIntoView(true);', bonus)
                bonus.click()
                        
                if popup_box_html.find('icon header premium') != -1:
                    WebDriverWait(driver, 2, 0.25).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="popup_box_daily_bonus"]/div/a'))).click()
                
                for _ in range(30):
                    try:
                        driver.find_element_by_id('popup_box_daily_bonus')
                        time.sleep(0.05)
                    except:
                        break            
                return True

            except BaseException:  
                logging.error(f'{time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())} {traceback.format_exc()}')
                return False

        # zamknij wszystkie popup_boxy które nie dotyczą bonusu dziennego
        else:
            driver.find_element_by_xpath('//*[@id="ds_body"]/div[@class="popup_box_container"]/div/div/a').click()
            for _ in range(30):
                try:
                    driver.find_element_by_xpath('//*[@id="ds_body"]/div[@class="popup_box_container"]')
                    time.sleep(0.05)
                except:
                    break
            return True

    # zamyka otwarte okno grup    
    elif driver.find_elements_by_xpath('//*[@id="open_groups"][@style="display: none;"]'):
        close_group = driver.find_element_by_id('closelink_group_popup')
        driver.execute_script('return arguments[0].scrollIntoView(true);', close_group)
        close_group.click()

    # nieznane -> log_error
    else:
        log_error(driver)
        return False