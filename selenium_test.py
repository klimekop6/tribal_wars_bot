from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from math import sqrt
import time

import logging
logging.basicConfig(filename='log.txt', level=logging.ERROR)

def log_in() -> None:
    """ logowanie """

    driver.get('https://www.plemiona.pl/page/play/pl160')

    username = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,'input[name="username"]')))
    password = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,'input[name="password"]')))

    username.clear()
    password.clear()
    username.send_keys('klimekop6')
    password.send_keys('u56708')

    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'btn-login'))).click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Świat 160"]'))).click()

def attacks_labels() -> None:
    """ etykiety ataków """

    if not driver.find_element_by_id('incomings_amount').text:
        return    
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'incomings_cell'))).click() # otwarcie karty z nadchodzącymi atakami
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[1]/*[@data-group-type="all"]'))).click() # zmiana grupy na wszystkie
    manage_filters = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a'))) # zwraca element z filrem ataków
    if driver.find_element_by_xpath('//*[@id="paged_view_content"]/div[2]').get_attribute('style').find('display: none') != -1:
        manage_filters.click()
    etkyieta_rozkazu = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[2]/td[2]/input')))

    etkyieta_rozkazu.clear()
    etkyieta_rozkazu.send_keys('Atak')

    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/div[2]/form/table/tbody/tr[7]/td/input'))).click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paged_view_content"]/a')))
    try:
        driver.find_element_by_id('incomings_table')
    except:
        return

    element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'select_all')))
    driver.execute_script('return arguments[0].scrollIntoView(true);', element)
    element.click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//input[@value="Etykieta"]'))).click()

def dodge_attacks() -> None:
    """ unika wybranej wielkości offów """    

    villages = player_villages()

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

def player_villages() -> dict:
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

def market_offers() -> None:
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

def send_back_support() -> None:
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
            
def mark_villages_on_map() -> None:
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

if __name__ == "__main__":
    #    txt = 'txt'
    #    try:
    #        int(txt)
    #    except ValueError:
    #        logging.error('Wprowadzono inne znaki niż cyfry!')

    while True:
        driver = webdriver.Chrome('chromedriver.exe')
        log_in()
        attacks_labels()
        driver.close()
        time.sleep(900)