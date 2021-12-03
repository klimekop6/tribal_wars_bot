import ctypes
import datetime
import json
import logging
import os
import subprocess
import random
import sys
import threading
import time
from tkinter import *
from tkinter.ttk import *
from functools import partial

import pyodbc
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from ttkbootstrap import Style

import bot_functions
import email_notifications

logging.basicConfig(filename='log.txt', level=logging.ERROR)

# Context manager
class DataBaseConnection:

    def __init__(self) -> None:
        self.cnxn = None
        self.cursor = None

    def __enter__(self):
        try:
            self.cnxn = pyodbc.connect('''DRIVER={ODBC Driver 17 for SQL Server};
                                        SERVER=***REMOVED***;
                                        DATABASE=Plemiona;
                                        UID=***REMOVED***;
                                        PWD=***REMOVED***''',
                                        timeout=3)             
            self.cursor = self.cnxn.cursor()
            return self.cursor
        except pyodbc.OperationalError:
            pass      
            
    def __exit__(self, exc_type, exc_value, exc_tracebac):
        if not self.cnxn:
            MyFunc().custom_error('Serwer jest tymczasowo niedostępny.')           
            return True
        self.cnxn.commit()
        self.cnxn.close()


class MyFunc:

    def center(window, parent=None) -> None:
        """Place window in the center of a screen or parent widget"""

        if parent:
            parent_geometry = parent.winfo_geometry()
            parent_x, parent_y = parent_geometry[parent_geometry.find('+')+1:].split('+')
            window.update_idletasks()
            window.geometry(f'+{int(int(parent.winfo_rootx()) + parent.winfo_reqwidth()/2 - window.winfo_reqwidth()/2)}'
                            f'+{int(int(parent.winfo_rooty()) + parent.winfo_reqheight()/2 - window.winfo_reqheight()/2)}')

        else:
            window.update_idletasks()
            window.geometry(f'+{int(window.winfo_screenwidth()/2 - window.winfo_reqwidth()/2)}'
                            f'+{int(window.winfo_screenheight()/2 - window.winfo_reqheight()/2)}')

    def change_state(parent, value, entries_content, reverse=False, *ommit) -> None:

        def disableChildren(parent):
            if not parent.winfo_children():
                if parent.winfo_class() not in ('TFrame', 'Labelframe', 'TSeparator'):
                    parent.config(state='disabled')
            for child in parent.winfo_children():
                wtype = child.winfo_class()
                if wtype not in ('TFrame', 'Labelframe', 'TSeparator'):
                    if child not in ommit:
                        child.configure(state='disable')
                else:
                    disableChildren(child)

        def enableChildren(parent):
            if not parent.winfo_children():
                if parent.winfo_class() not in ('TFrame', 'Labelframe', 'TSeparator'):
                    parent.config(state='normal')
            for child in parent.winfo_children():
                wtype = child.winfo_class()
                if wtype not in ('TFrame', 'Labelframe', 'TSeparator'):
                    if child not in ommit:
                        child.configure(state='normal')
                else:
                    enableChildren(child)

        def check_button_fix(parent):
            for child in parent.winfo_children():
                wtype = child.winfo_class()
                if wtype in ('TCheckbutton'):
                    if child not in ommit:
                        child.invoke()
                        child.invoke()
                
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

    def change_state_on_settings_load(parent, name, entries_content, reverse=False, *ommit) -> None:
        if name in entries_content:
            if not entries_content[name].get():
                return
            if int(entries_content[name].get()) or reverse:
                MyFunc.change_state(parent, int(entries_content[name].get()), entries_content, reverse, *ommit) 

    def chrome_profile_path() -> None:
        """Wyszukuję i zapisuje w ustawieniach aplikacji aktualną ścierzkę do profilu użytkownika przeglądarki chrome"""

        driver = webdriver.Chrome('chromedriver.exe')
        driver.get('chrome://version')
        path = driver.find_element_by_xpath('//*[@id="profile_path"]').text
        driver.quit()
        path = path[:path.find('Temp\\')] + 'Google\\Chrome\\User Data'
        settings['path'] = path
        settings['first_lunch'] = False
        settings['last_opened_daily_bonus'] = time.strftime("%d.%m.%Y", time.localtime())

        with open('settings.json', 'w') as settings_json_file:
            json.dump(settings, settings_json_file)
    
    def current_time() -> str:
        return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())

    def custom_error(self, message: str) -> None:
        
        self.master = Toplevel(borderwidth=1, relief='groove')
        self.master.overrideredirect(True)
        self.master.attributes('-topmost', 1)        
        self.master.bell()

        self.message_label = Label(self.master, text=message)
        self.message_label.grid(row=1, column=0, padx=5, pady=5)

        self.ok_button = Button(self.master, text='ok', command=self.master.destroy)
        self.ok_button.grid(row=2, column=0, pady=(5,8))
     
        self.message_label.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'message_label'))
        self.ok_button.focus_force()
        self.ok_button.bind('<Return>', lambda event: self.master.destroy())
        MyFunc.center(self.master)

    def fill_entry_from_settings(entries: dict) -> None:

        for key in entries:
            if key in settings:
                if settings[key]:
                    if isinstance(settings[key], dict):
                        for key_ in settings[key]:
                            if settings[key][key_]:
                                if isinstance(settings[key][key_], dict):
                                    for _key_ in settings[key][key_]:
                                        if settings[key][key_][_key_]:
                                            if isinstance(settings[key][key_][_key_], dict):
                                                for __key__ in settings[key][key_][_key_]:
                                                    if settings[key][key_][_key_][__key__]:
                                                        entries[key][key_][_key_][__key__].set(settings[key][key_][_key_][__key__])
                                                    else:
                                                        entries[key][key_][_key_][__key__].set(0)
                                            else:
                                                entries[key][key_][_key_].set(settings[key][key_][_key_])
                                        else:
                                            entries[key][key_][_key_].set(0)
                                else:                                    
                                    entries[key][key_].set(settings[key][key_])
                            else:
                                entries[key][key_].set(0)
                    else:
                        entries[key].set(settings[key])
                else:
                    entries[key].set(0)

    def first_app_lunch() -> None:
        """Do some stuff if app was just installed for the 1st time"""     

        def is_admin():
            try:
                return ctypes.windll.shell32.IsUserAnAdmin()
            except:
                return False

        if is_admin():
            # Code of your program here
            subprocess.run('regedit /s anticaptcha-plugin.reg')
            MyFunc.chrome_profile_path()
        else:
            # Re-run the program with admin rights
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
            sys.exit()

    def get_pos(self, event, *args) -> None:
        xwin = self.master.winfo_x()
        ywin = self.master.winfo_y()
        startx = event.x_root
        starty = event.y_root

        ywin = ywin - starty
        xwin = xwin - startx

        def move_window(event):
            self.master.geometry(f'+{event.x_root + xwin}+{event.y_root + ywin}')
        startx = event.x_root
        starty = event.y_root

        for arg in args:
            getattr(self, arg).bind('<B1-Motion>', move_window)

    def if_paid(date: str) -> bool:
        if time.strptime(MyFunc.current_time(), '%d/%m/%Y %H:%M:%S') > time.strptime(date + ' 23:59:59', '%Y-%m-%d %H:%M:%S'):
            return False
        return True
    
    def load_settings(file_path: str='settings.json') -> dict:
        try:
            f = open(file_path)
            settings = json.load(f)
        except FileNotFoundError:
            f = open('settings.json', 'w')
            settings = {'first_lunch': True}
            settings["gathering_troops"] = {"spear": {"use": False, "left_in_village": 0},
                                            "sword": {"use": False, "left_in_village": 0}, 
                                            "axe": {"use": False, "left_in_village": 0}, 
                                            "archer": {"use": False, "left_in_village": 0}, 
                                            "light": {"use": False, "left_in_village": 0}, 
                                            "marcher": {"use": False, "left_in_village": 0}, 
                                            "heavy": {"use": False, "left_in_village": 0}, 
                                            "knight": {"use": False, "left_in_village": 0}}
            json.dump(settings, f)
        finally:
            f.close()            
            return settings

    def run_driver(headless: bool=False) -> None:
        """Uruchamia sterownik i przeglądarkę google chrome"""
        
        global driver
        try:
            if headless:
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('user-data-dir=' + settings['path'])
                return webdriver.Chrome('chromedriver.exe', options=chrome_options)
            else:
                chrome_options = Options()
                chrome_options.add_argument('user-data-dir=' + settings['path'])
                chrome_options.add_extension(extension='0.60_0.crx')
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])   
                driver = webdriver.Chrome('chromedriver.exe', options=chrome_options)
                driver.maximize_window()
        except BaseException as exc:
            logging.error(exc)

    def save_entry_to_settings(entries: dict) -> None:

        for key, value in entries.items():
            if isinstance(value, dict):
                for key_ in value:
                    if key not in settings:
                        settings[key] = {}
                    if isinstance(value[key_], dict):
                        for _key_ in value[key_]:
                            if key_ not in settings[key]:
                                settings[key][key_] = {}
                            if isinstance(value[key_][_key_], dict):
                                for __key__ in value[key_][_key_]:
                                    if _key_ not in settings[key][key_]:
                                        settings[key][key_][_key_] = {}
                                    settings[key][key_][_key_][__key__] = value[key_][_key_][__key__].get()
                            else:
                                settings[key][key_][_key_] = value[key_][_key_].get()
                    else:
                        settings[key][key_] = value[key_].get()
            else:
                settings[key] = value.get()
                
        with open('settings.json', 'w') as settings_json_file:
            json.dump(settings, settings_json_file)

        if not os.path.isdir('settings'):
            os.mkdir('settings')

        with open(f'settings/{settings["world_number"]}.json', 'w') as settings_json_file:
            json.dump(settings, settings_json_file)


class MainWindow:
    
    entries_content = {}
    elements_state = []

    def __init__(self) -> None:
        self.master = Tk()
        self.master.attributes('-alpha', 0.0)
        self.master.iconbitmap(default='icons//ikona.ico')        
        self.master.title('Tribal Wars 24/7')        
        self.master.overrideredirect(True)
        self.master.attributes('-topmost', 1)

        # main_frame -> custom_bar, content_frame
        self.main_frame = Frame(self.master, borderwidth=1, relief='groove')
        self.main_frame.grid(row=0, column=0, sticky=(N, S, E, W))

        self.custom_bar = Frame(self.main_frame)
        self.custom_bar.grid(row=0, column=0, sticky=(N, S, E, W))
        self.custom_bar.columnconfigure(3, weight=1)

        self.content_frame = Frame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky=(N, S, E, W))

        # custom_bar
        self.title_label = Label(self.custom_bar, text='Tribal Wars Bot')
        self.title_label.grid(row=0, column=1, padx=(5, 0) , sticky=W)

        self.time = StringVar()
        self.title_timer = Label(self.custom_bar, textvariable=self.time)
        self.title_timer.grid(row=0, column=2, padx=5)

        self.entries_content['world_in_title'] = StringVar(value=' ')
        self.title_world = Label(self.custom_bar, textvariable=self.entries_content['world_in_title'])
        self.title_world.grid(row=0, column=3, padx=(5, 0), sticky=E)

        self.photo = PhotoImage(file='icons//minimize.png')
        self.minimize = self.photo.subsample(2, 2)

        self.minimize_button = Button(self.custom_bar, style='primary.Link.TButton', image=self.minimize, command=self.hide)
        self.minimize_button.grid(row=0, column=4, padx=(5, 0), pady=5, sticky=E)

        self.photo = PhotoImage(file='icons//exit.png')
        self.exit = self.photo.subsample(8, 8)

        self.exit_button = Button(self.custom_bar, style='primary.Link.TButton', image=self.exit, 
                                command= lambda: [MyFunc.save_entry_to_settings(self.entries_content),
                                subprocess.run('taskkill /IM chromedriver.exe /F') if driver else None, self.master.destroy()])
        self.exit_button.grid(row=0, column=5, padx=(0, 5), pady=3, sticky=E)      

        self.custom_bar.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'custom_bar'))
        self.title_label.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'title_label'))
        self.title_world.bind('<Button-1>', lambda event: self.show_world_chooser_window(event))
        self.title_timer.bind('<Button-1>', lambda event: self.show_jobs_to_do_window(event))

        # content_frame

        # Notebook with frames 
        n = Notebook(self.content_frame)
        n.grid(row=1, column=0, padx=5, pady=(0, 5), sticky=(N, S, E, W))
        f1 = Frame(n)
        f2 = Frame(n)
        f3 = Frame(n)
        f4 = Frame(n)
        f5 = Frame(n)
        n.add(f1, text='Farma')
        n.add(f2, text='Zbieractwo')
        n.add(f3, text='Planer')
        n.add(f4, text='Rynek')
        n.add(f5, text='Ustawienia')        
        self.content_frame.rowconfigure(0, weight=1)
        self.content_frame.columnconfigure(0, weight=1)

        # f1 -> 'Farma'
        templates = Notebook(f1)
        templates.grid(pady=5, padx=5, sticky=(N, S, E, W))
        A = Frame(templates)
        B = Frame(templates)
        C = Frame(templates)
        templates.add(A, text='Szablon A')
        templates.add(B, text='Szablon B')
        templates.add(C, text='Szablon C')
        f1.rowconfigure(0, weight=1)
        f1.columnconfigure(0, weight=1)

        # Szablon A
        #region
        A.columnconfigure(0, weight=1)
        A.columnconfigure(1, weight=1)
        self.entries_content['A'] = {}

        self.entries_content['A']['active'] = StringVar()
        self.active_A = Checkbutton(A, text='Aktywuj szablon', 
                                    variable=self.entries_content['A']['active'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: MyFunc.change_state(*self.elements_state[0]))
        self.active_A.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
        self.elements_state.append([A, 'active', self.entries_content['A'], True, self.active_A])
        
        Separator(A, orient=HORIZONTAL).grid(row=1, column=0, columnspan=2, sticky=(W, E))

        self.wall = Label(A, text='Poziom muru')
        self.wall.grid(row=2, column=0, columnspan=2, pady=(20, 15), padx=5, sticky=W)

        self.entries_content['A']['wall_ignore'] = StringVar()
        self.wall_ignore = Checkbutton(A, text='Ignoruj poziom', 
                                       variable=self.entries_content['A']['wall_ignore'], 
                                       onvalue=True, offvalue=False,
                                       command=lambda: MyFunc.change_state(*self.elements_state[1]))
        self.wall_ignore.grid(row=3, column=0, pady=5, padx=(25, 5), sticky=W)     

        self.min_wall_level = Label(A, text='Min')
        self.min_wall_level.grid(row=4, column=0, pady=5, padx=(25, 5), sticky=W)

        self.entries_content['A']['min_wall'] = StringVar()
        self.min_wall_level_input = Entry(A, width=5, textvariable=self.entries_content['A']['min_wall'], justify='center')
        self.min_wall_level_input.grid(row=4, column=1, pady=5, padx=(5, 25), sticky=E)

        self.max_wall_level = Label(A, text='Max')
        self.max_wall_level.grid(row=5, column=0, pady=5, padx=(25, 5), sticky=W)

        self.entries_content['A']['max_wall'] = StringVar()
        self.max_wall_level_input_A = Entry(A, width=5, textvariable=self.entries_content['A']['max_wall'], justify='center')
        self.max_wall_level_input_A.grid(row=5, column=1, pady=5, padx=(5, 25), sticky=E)
        self.elements_state.append([[self.min_wall_level_input, self.max_wall_level_input_A], 'wall_ignore', self.entries_content['A']])               

        self.attacks = Label(A, text='Wysyłka ataków')
        self.attacks.grid(row=6, column=0, columnspan=2, pady=(20, 10), padx=5, sticky=W)        

        self.entries_content['A']['max_attacks'] = StringVar()
        self.max_attacks_A = Checkbutton(A, text='Maksymalna ilość', 
                                    variable=self.entries_content['A']['max_attacks'], 
                                    onvalue=True, offvalue=False, 
                                    command=lambda: MyFunc.change_state(*self.elements_state[2]))
        self.max_attacks_A.grid(row=7, column=0, pady=5, padx=(25, 5), sticky=W)

        self.attacks = Label(A, text='Ilość ataków')
        self.attacks.grid(row=8, column=0, pady=(5, 10), padx=(25, 5), sticky=W)

        self.entries_content['A']['attacks_number'] = StringVar()
        self.attacks_number_input_A = Entry(A, width=5, textvariable=self.entries_content['A']['attacks_number'], justify='center')
        self.attacks_number_input_A.grid(row=8, column=1, pady=(5, 10), padx=(5, 25), sticky=E)
        self.elements_state.append([self.attacks_number_input_A, 'max_attacks', self.entries_content['A']])
        #endregion
        
        # Szablon B
        #region
        B.columnconfigure(0, weight=1)
        B.columnconfigure(1, weight=1)
        self.entries_content['B'] = {}
        
        self.entries_content['B']['active'] = StringVar()
        self.active_B = Checkbutton(B, text='Aktywuj szablon', 
                                    variable=self.entries_content['B']['active'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: MyFunc.change_state(*self.elements_state[3]))
        self.active_B.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
        self.elements_state.append([B, 'active', self.entries_content['B'], True, self.active_B])

        Separator(B, orient=HORIZONTAL).grid(row=1, column=0, columnspan=2, sticky=(W, E))

        self.wall = Label(B, text='Poziom muru')
        self.wall.grid(row=2, column=0, columnspan=2, pady=(20, 15), padx=5, sticky=W)

        self.entries_content['B']['wall_ignore'] = StringVar()
        self.wall_ignore_B = Checkbutton(B, text='Ignoruj poziom', 
                                       variable=self.entries_content['B']['wall_ignore'], 
                                       onvalue=True, offvalue=False,
                                       command=lambda: MyFunc.change_state(*self.elements_state[4]))
        self.wall_ignore_B.grid(row=3, column=0, pady=5, padx=(25, 5), sticky=W)          

        self.min_wall_level = Label(B, text='Min')
        self.min_wall_level.grid(row=4, column=0, pady=5, padx=(25, 5), sticky=W)

        self.entries_content['B']['min_wall'] = StringVar()
        self.min_wall_level_input_B = Entry(B, width=5, textvariable=self.entries_content['B']['min_wall'], justify='center')
        self.min_wall_level_input_B.grid(row=4, column=1, pady=5, padx=(5, 25), sticky=E)

        self.max_wall_level = Label(B, text='Max')
        self.max_wall_level.grid(row=5, column=0, pady=5, padx=(25, 5), sticky=W)

        self.entries_content['B']['max_wall'] = StringVar()
        self.max_wall_level_input_B = Entry(B, width=5, textvariable=self.entries_content['B']['max_wall'], justify='center')
        self.max_wall_level_input_B.grid(row=5, column=1, pady=5, padx=(5, 25), sticky=E)
        self.elements_state.append([[self.min_wall_level_input_B, self.max_wall_level_input_B], 'wall_ignore', self.entries_content['B']])               

        self.attacks = Label(B, text='Wysyłka ataków')
        self.attacks.grid(row=6, column=0, columnspan=2, pady=(20, 10), padx=5, sticky=W)        

        self.entries_content['B']['max_attacks'] = StringVar()
        self.max_attacks_B = Checkbutton(B, text='Maksymalna ilość', 
                                    variable=self.entries_content['B']['max_attacks'], 
                                    onvalue=True, offvalue=False, 
                                    command=lambda: MyFunc.change_state(*self.elements_state[5]))
        self.max_attacks_B.grid(row=7, column=0, pady=5, padx=(25, 5), sticky=W)

        self.attacks = Label(B, text='Ilość ataków')
        self.attacks.grid(row=8, column=0, pady=(5, 10), padx=(25, 5), sticky=W)

        self.entries_content['B']['attacks_number'] = StringVar()
        self.attacks_number_input_B = Entry(B, width=5, textvariable=self.entries_content['B']['attacks_number'], justify='center')
        self.attacks_number_input_B.grid(row=8, column=1, pady=(5, 10), padx=(5, 25), sticky=E)
        self.elements_state.append([self.attacks_number_input_B, 'max_attacks', self.entries_content['B']])
        #endregion        
        
        # Szablon C
        #region
        C.columnconfigure(1, weight=1)
        C.columnconfigure(0, weight=1)
        self.entries_content['C'] = {}

        self.entries_content['C']['active'] = StringVar()
        self.active_C = Checkbutton(C, text='Aktywuj szablon', 
                                    variable=self.entries_content['C']['active'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: MyFunc.change_state(*self.elements_state[6]))
        self.active_C.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
        self.elements_state.append([C, 'active', self.entries_content['C'], True, self.active_C])

        Separator(C, orient=HORIZONTAL).grid(row=1, column=0, columnspan=2, sticky=(W, E))

        self.wall = Label(C, text='Poziom muru')
        self.wall.grid(row=2, column=0, columnspan=2, pady=(20, 15), padx=5, sticky=W)

        self.entries_content['C']['wall_ignore'] = StringVar()
        self.wall_ignore_C = Checkbutton(C, text='Ignoruj poziom', 
                                       variable=self.entries_content['C']['wall_ignore'], 
                                       onvalue=True, offvalue=False,
                                       command=lambda: MyFunc.change_state(*self.elements_state[7]))
        self.wall_ignore_C.grid(row=3, column=0, pady=5, padx=(25, 5), sticky=W)  

        self.min_wall_level = Label(C, text='Min')
        self.min_wall_level.grid(row=4, column=0, pady=5, padx=(25, 5), sticky=W)

        self.entries_content['C']['min_wall'] = StringVar()
        self.min_wall_level_input_C = Entry(C, width=5, textvariable=self.entries_content['C']['min_wall'], justify='center')
        self.min_wall_level_input_C.grid(row=4, column=1, pady=5, padx=(5, 25), sticky=E)

        self.max_wall_level = Label(C, text='Max')
        self.max_wall_level.grid(row=5, column=0, pady=5, padx=(25, 5), sticky=W)

        self.entries_content['C']['max_wall'] = StringVar()
        self.max_wall_level_input_C = Entry(C, width=5, textvariable=self.entries_content['C']['max_wall'], justify='center')
        self.max_wall_level_input_C.grid(row=5, column=1, pady=5, padx=(5, 25), sticky=E)
        self.elements_state.append([[self.min_wall_level_input_C, self.max_wall_level_input_C], 'wall_ignore', self.entries_content['C']])               

        self.attacks = Label(C, text='Wysyłka ataków')
        self.attacks.grid(row=6, column=0, pady=(20, 10), padx=5, sticky=W)        

        self.entries_content['C']['max_attacks'] = StringVar()
        self.max_attacks_C = Checkbutton(C, text='Maksymalna ilość', 
                                    variable=self.entries_content['C']['max_attacks'], 
                                    onvalue=True, offvalue=False, 
                                    command=lambda: MyFunc.change_state(*self.elements_state[8]))
        self.max_attacks_C.grid(row=7, column=0, pady=5, padx=(25, 5), sticky=W)

        self.attacks = Label(C, text='Ilość ataków')
        self.attacks.grid(row=8, column=0, pady=(5, 10), padx=(25, 5), sticky=W)

        self.entries_content['C']['attacks_number'] = StringVar()
        self.attacks_number_input_C = Entry(C, width=5, textvariable=self.entries_content['C']['attacks_number'], justify='center')
        self.attacks_number_input_C.grid(row=8, column=1, pady=(5, 10), padx=(5, 25), sticky=E)
        self.elements_state.append([self.attacks_number_input_C, 'max_attacks', self.entries_content['C']])
        #endregion

        # f2 -> 'Zbieractwo'
        #region
        f2.columnconfigure(0, weight=1)
        
        self.entries_content['gathering'] = {}
        self.entries_content['gathering_troops'] = {'spear': {'left_in_village': StringVar()},
                                                    'sword': {'left_in_village': StringVar()}, 
                                                    'axe': {'left_in_village': StringVar()}, 
                                                    'archer': {'left_in_village': StringVar()}, 
                                                    'light': {'left_in_village': StringVar()}, 
                                                    'marcher': {'left_in_village': StringVar()}, 
                                                    'heavy': {'left_in_village': StringVar()}, 
                                                    'knight': {'left_in_village': StringVar()}}

        self.entries_content['gathering']['active'] = StringVar()
        self.active_gathering = Checkbutton(f2, text='Aktywuj zbieractwo', 
                                    variable=self.entries_content['gathering']['active'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: MyFunc.change_state(*self.elements_state[9]))
        self.active_gathering.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
        self.elements_state.append([f2, 'active', self.entries_content['gathering'], True, self.active_gathering])
        
        Separator(f2, orient=HORIZONTAL).grid(row=1, column=0, columnspan=2, sticky=(W, E))

        Label(f2, text='Ustawienia').grid(row=5, columnspan=2, padx=5, pady=(20, 15), sticky=W)     

        Label(f2 , text='Grupa zbieractwa').grid(row=6, column=0, padx=(25, 5), pady=5, sticky=W)        

        self.entries_content['gathering_group'] = StringVar()
        if 'groups' not in settings:
            settings['groups'] = None
        self.gathering_group = Combobox(f2, textvariable=self.entries_content['gathering_group'], justify=CENTER, width=16)
        self.gathering_group.grid(row=6, column=1, padx=(5, 25), pady=5, sticky=E)
        self.gathering_group.set('Wybierz grupę')
        self.gathering_group['values'] = settings['groups']

        self.gathering_max_resources = Label(f2, text='Maks surowców do zebrania')
        self.gathering_max_resources.grid(row=7, column=0, padx=(25, 5), pady=(10, 5), sticky=W)

        self.entries_content['gathering_max_resources'] = StringVar()
        self.gathering_max_resources_input = Entry(f2, textvariable=self.entries_content['gathering_max_resources'], justify=CENTER, width=18)
        self.gathering_max_resources_input.grid(row=7, column=1, padx=(5, 25), pady=(10, 5), sticky=E)

        Label(f2, text='Dozwolone jednostki do wysłania').grid(row=8, columnspan=2, padx=5, pady=(20, 15), sticky=W)

        self.entries_content['gathering_troops']['spear']['use'] = StringVar()
        self.spear_photo = PhotoImage(file='icons//spear.png')
        self.gathering_spear = Checkbutton(f2, text='Pikinier', image=self.spear_photo, compound=LEFT, 
                                    variable=self.entries_content['gathering_troops']['spear']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_spear.grid(row=9, column=0, padx=(25, 5), pady=5, sticky=W)

        self.entries_content['gathering_troops']['light']['use'] = StringVar()
        self.light_photo = PhotoImage(file='icons//light.png')
        self.gathering_light = Checkbutton(f2, text='Lekka kawaleria', image=self.light_photo, compound=LEFT, 
                                    variable=self.entries_content['gathering_troops']['light']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_light.grid(row=9, column=1, padx=(5, 25), pady=5, sticky=W)

        self.entries_content['gathering_troops']['sword']['use'] = StringVar()
        self.sword_photo = PhotoImage(file='icons//sword.png')
        self.gathering_sword = Checkbutton(f2, text='Miecznik', image=self.sword_photo, compound=LEFT, 
                                    variable=self.entries_content['gathering_troops']['sword']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_sword.grid(row=10, column=0, padx=(25, 5), pady=5, sticky=W)

        self.entries_content['gathering_troops']['marcher']['use'] = StringVar()
        self.marcher_photo = PhotoImage(file='icons//marcher.png')
        self.gathering_marcher = Checkbutton(f2, text='Łucznik konny', image=self.marcher_photo, compound=LEFT, 
                                    variable=self.entries_content['gathering_troops']['marcher']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_marcher.grid(row=10, column=1, padx=(5, 25), pady=5, sticky=W)

        self.entries_content['gathering_troops']['axe']['use'] = StringVar()
        self.axe_photo = PhotoImage(file='icons//axe.png')
        self.gathering_axe = Checkbutton(f2, text='Topornik', image=self.axe_photo, compound=LEFT, 
                                    variable=self.entries_content['gathering_troops']['axe']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_axe.grid(row=11, column=0, padx=(25, 5), pady=5, sticky=W)

        self.entries_content['gathering_troops']['heavy']['use'] = StringVar()
        self.heavy_photo = PhotoImage(file='icons//heavy.png')
        self.gathering_heavy = Checkbutton(f2, text='Ciężki kawalerzysta', image=self.heavy_photo, compound=LEFT, 
                                    variable=self.entries_content['gathering_troops']['heavy']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_heavy.grid(row=11, column=1, padx=(5, 25), pady=5, sticky=W)

        self.entries_content['gathering_troops']['archer']['use'] = StringVar()
        self.archer_photo = PhotoImage(file='icons//archer.png')
        self.gathering_archer = Checkbutton(f2, text='Łucznik', image=self.archer_photo, compound=LEFT, 
                                    variable=self.entries_content['gathering_troops']['archer']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_archer.grid(row=12, column=0, padx=(25, 5), pady=(5, 10), sticky=W)

        self.entries_content['gathering_troops']['knight']['use'] = StringVar()
        self.knight_photo = PhotoImage(file='icons//knight.png')
        self.gathering_knight = Checkbutton(f2, text='Rycerz', image=self.knight_photo, compound=LEFT, 
                                    variable=self.entries_content['gathering_troops']['knight']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_knight.grid(row=12, column=1, padx=(5, 25), pady=(5, 10), sticky=W)

        Label(f2, text='Poziomy zbieractwa do pominięcia').grid(row=13, columnspan=2, padx=5, pady=(20, 15), sticky=W)

        f2_1 = Frame(f2)
        f2_1.grid(row=14, column=0, columnspan=2)

        self.entries_content['gathering']['ommit'] = {}

        self.entries_content['gathering']['ommit']['first_level_gathering'] = StringVar()
        self.ommit_first_level_gathering = Checkbutton(f2_1, text='Pierwszy', 
                                    variable=self.entries_content['gathering']['ommit']['first_level_gathering'], 
                                    onvalue=True, offvalue=False)
        self.ommit_first_level_gathering.grid(row=14, column=0, padx=(25, 5), pady=(5, 10))

        self.entries_content['gathering']['ommit']['second_level_gathering'] = StringVar()
        self.ommit_second_level_gathering = Checkbutton(f2_1, text='Drugi', 
                                    variable=self.entries_content['gathering']['ommit']['second_level_gathering'], 
                                    onvalue=True, offvalue=False)
        self.ommit_second_level_gathering.grid(row=14, column=1, padx=10, pady=(5, 10))

        self.entries_content['gathering']['ommit']['thrid_level_gathering'] = StringVar()
        self.ommit_thrid_level_gathering = Checkbutton(f2_1, text='Trzeci', 
                                    variable=self.entries_content['gathering']['ommit']['thrid_level_gathering'], 
                                    onvalue=True, offvalue=False)
        self.ommit_thrid_level_gathering.grid(row=14, column=2, padx=10, pady=(5, 10))

        self.entries_content['gathering']['ommit']['fourth_level_gathering'] = StringVar()
        self.ommit_fourth_level_gathering = Checkbutton(f2_1, text='Czwarty', 
                                    variable=self.entries_content['gathering']['ommit']['fourth_level_gathering'], 
                                    onvalue=True, offvalue=False)
        self.ommit_fourth_level_gathering.grid(row=14, column=3, padx=(5, 25), pady=(5, 10))

        self.entries_content['gathering']['stop_if_incoming_attacks'] = StringVar()
        self.stop_if_incoming_attacks = Checkbutton(f2, text='Wstrzymaj wysyłkę wojsk gdy wykryto nadchodzące ataki', 
                                    variable=self.entries_content['gathering']['stop_if_incoming_attacks'], 
                                    onvalue=True, offvalue=False)
        self.stop_if_incoming_attacks.grid(row=15, column=0, columnspan=2, padx=25, pady=(10, 5), sticky=W)

        #endregion

        # f3 -> 'Planer'
        f3.columnconfigure(0, weight=1)
        f3.columnconfigure(1, weight=1)

        Label(f3, text='Wioski startowe').grid(row=0, column=0, padx=5, pady=10)
        Label(f3, text='Wioski docelowe').grid(row=0, column=1, padx=5, pady=10)

        self.villages_to_use = Text(f3, wrap='word', height=5, width=15).grid(row=1, column=0, padx=5, pady=(0, 5))
        self.villages_destiny = Text(f3, wrap='word', height=5, width=15).grid(row=1, column=1, padx=5, pady=(0, 5))

        Label(f3, text='Rodzaj komendy').grid(row=2, column=0, columnspan=2, padx=5, pady=(10, 5))
        command_type = StringVar()
        self.command_type_attack = Radiobutton(f3, text='Atak', value='target_attack', variable=command_type).grid(row=3, column=0, padx=5, pady=5)
        self.command_type_support = Radiobutton(f3, text='Wsparcie', value='target_support', variable=command_type).grid(row=3, column=1, padx=5, pady=5)

        Label(f3, text='Data dotarcia').grid(row=4, column=0, columnspan=2, padx=5, pady=(10, 5))


        # f4 -> 'Rynek'
        #region
        f4.columnconfigure(0, weight=1)
        
        self.entries_content['market'] = {'wood': {}, 'stone': {}, 'iron': {}}

        self.entries_content['premium_exchange'] = StringVar()
        self.active_premium_exchange = Checkbutton(f4, text='Aktywuj giełde premium', 
                                    variable=self.entries_content['premium_exchange'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: MyFunc.change_state(*self.elements_state[10]))
        self.active_premium_exchange.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
        self.elements_state.append([f4, 'premium_exchange', self.entries_content, True, self.active_premium_exchange])
        
        Separator(f4, orient=HORIZONTAL).grid(row=1, column=0, columnspan=2, sticky=(W, E))

        # Label(f4, text='Ustawienia').grid(row=2, columnspan=2, padx=5, pady=(20, 15), sticky=W)  

        Label(f4 , text='Maksymalny kurs sprzedaży').grid(row=3, column=0, padx=5, pady=(20, 15), sticky=W)

        self.wood_photo = PhotoImage(file='icons//wood.png')
        Label(f4, text='Drewno', image=self.wood_photo, compound=LEFT).grid(row=4, column=0, padx=(25, 5), pady=5, sticky=W)
        self.entries_content['market']['wood']['max_exchange_rate'] = StringVar()
        self.max_wood_exchange_rate = Entry(f4, textvariable=self.entries_content['market']['wood']['max_exchange_rate'], justify=CENTER, width=6)
        self.max_wood_exchange_rate.grid(row=4, column=1, padx=(5, 25), pady=(10, 5), sticky=E)        


        self.stone_photo = PhotoImage(file='icons//stone.png')
        Label(f4, text='Cegła', image=self.stone_photo, compound=LEFT).grid(row=5, column=0, padx=(25, 5), pady=5, sticky=W)
        self.entries_content['market']['stone']['max_exchange_rate'] = StringVar()
        self.max_stone_exchange_rate = Entry(f4, textvariable=self.entries_content['market']['stone']['max_exchange_rate'], justify=CENTER, width=6)
        self.max_stone_exchange_rate.grid(row=5, column=1, padx=(5, 25), pady=(10, 5), sticky=E)  

        self.iron_photo = PhotoImage(file='icons//iron.png')
        Label(f4, text='Żelazo', image=self.iron_photo, compound=LEFT).grid(row=6, column=0, padx=(25, 5), pady=5, sticky=W)
        self.entries_content['market']['iron']['max_exchange_rate'] = StringVar()
        self.max_iron_exchange_rate = Entry(f4, textvariable=self.entries_content['market']['iron']['max_exchange_rate'], justify=CENTER, width=6)
        self.max_iron_exchange_rate.grid(row=6, column=1, padx=(5, 25), pady=(10, 5), sticky=E)

        def show_label_and_text_widget() -> None:
            
            def clear_text_widget(event) -> None:
                if self.villages_to_ommit_text.get('1.0', '1.5') == 'Wklej':
                    self.villages_to_ommit_text.delete('1.0', END)
                    self.villages_to_ommit_text.unbind('<Button-1>')

            def add_villages_list() -> None:
                if self.villages_to_ommit_text.get('1.0', '1.5') == 'Wklej':
                    self.entries_content['market_exclude_villages'].set('')
                else:
                    self.entries_content['market_exclude_villages'].set(self.villages_to_ommit_text.get('1.0', END))
                self.villages_to_ommit_text.grid_forget()
                self.confirm_button.grid_forget()

                self.success_label = Label(f4, text='Dodano!')
                self.success_label.grid(row=8, column=0, columnspan=2, padx=5, pady=15)
                self.master.update_idletasks()
                time.sleep(1)
                self.success_label.grid_forget()

            self.entries_content['market_exclude_villages'] = StringVar()
            self.villages_to_ommit_text = Text(f4, height=6, width=50, wrap='word')
            self.villages_to_ommit_text.grid(row=8, column=0, columnspan=2, padx=5, pady=10)
            if settings['market_exclude_villages']:
                self.villages_to_ommit_text.insert('1.0', settings['market_exclude_villages'])
            else:
                self.villages_to_ommit_text.insert('1.0', 'Wklej wioski w formacie XXX|YYY które chcesz aby były pomijane. Wioski powinny być oddzielone spacją, tabulatorem lub enterem.')

            self.confirm_button = Button(f4, text='Dodaj', command=add_villages_list)
            self.confirm_button.grid(row=9, column=0, columnspan=2, padx=5, pady=5)

            self.villages_to_ommit_text.bind('<Button-1>', clear_text_widget)

        self.add_village_exceptions_button = Button(f4, text='Dodaj wykluczenia', command=show_label_and_text_widget)
        self.add_village_exceptions_button.grid(row=7, column=0, columnspan=2, padx=5, pady=(30,5))    
        

        #endregion

        # f5 -> 'Ustawienia'
        f5.columnconfigure(0, weight=1)
        f5.columnconfigure(1, weight=1)

        self.world_number = Label(f5, text='Numer świata')
        self.world_number.grid(row=0, column=0, padx=5, pady=(10, 5), sticky=E)
        
        self.entries_content['world_number'] = StringVar()
        self.world_number_input = Entry(f5, textvariable=self.entries_content['world_number'], width=3, justify='center')
        self.world_number_input.grid(row=0, column=1, padx=5, pady=(10, 5), sticky=W)

        self.entries_content['farm_group'] = StringVar()
        self.farm_group = Combobox(f5, textvariable=self.entries_content['farm_group'])
        self.farm_group.grid(row=3, column=0, padx=5, pady=5, sticky=E)
        self.farm_group.set('Wybierz grupę')
        self.farm_group['values'] = settings['groups']

        self.update_groups = Button(f5, text='update', command=lambda: threading.Thread(target=self.check_groups, name='checking_groups', daemon=True).start())
        self.update_groups.grid(row=3, column=1, padx=5, pady=5, sticky=W)

        self.farm_sleep_time_label = Label(f5, text='Czas przed kolejnym wysłaniem farmy [min]')
        self.farm_sleep_time_label.grid(row=4, column=0, padx=5, pady=5, sticky=E)

        self.entries_content['farm_sleep_time'] = StringVar()
        self.farm_sleep_time = Entry(f5, textvariable=self.entries_content['farm_sleep_time'], width=5, justify='center')
        self.farm_sleep_time.grid(row=4, column=1, padx=5, pady=5, sticky=W)

        Button(f5, text='Zmień świat', command=self.add_new_world_settings).grid(row=5, columnspan=2, padx=5, pady=5)

        self.entries_content['account_premium'] = StringVar()
        self.account_premium = Checkbutton(f5, text='Konto premium', 
                                    variable=self.entries_content['account_premium'], 
                                    onvalue=True, offvalue=False)
        self.account_premium.grid(row=6, column=0, columnspan=2, padx=5, pady=20)

        self.entries_content['check_incoming_attacks'] = StringVar()
        self.check_incoming_attacks = Checkbutton(f5, text='Etykiety nadchodzących ataków', 
                                    variable=self.entries_content['check_incoming_attacks'], 
                                    onvalue=True, offvalue=False)
        self.check_incoming_attacks.grid(row=7, column=0, columnspan=2, padx=5, pady=10)

        self.check_incoming_attacks_label = Label(f5, text='Twórz etykiety ataków co [min]')
        self.check_incoming_attacks_label.grid(row=8, column=0, padx=5, pady=5, sticky=E)

        self.entries_content['check_incoming_attacks_sleep_time'] = StringVar()
        self.check_incoming_attacks_sleep_time = Entry(f5, textvariable=self.entries_content['check_incoming_attacks_sleep_time'], width=5, justify='center')
        self.check_incoming_attacks_sleep_time.grid(row=8, column=1, padx=5, pady=5, sticky=W)

        self.entries_content['email_notifications'] = StringVar()
        self.email_notifications = Checkbutton(f5, text='Powiadomienia email o idących grubasach', 
                                    variable=self.entries_content['email_notifications'], 
                                    onvalue=True, offvalue=False)
        self.email_notifications.grid(row=9, column=0, columnspan=2, padx=5, pady=10)

        # content_frame
        self.save_button = Button(self.content_frame, text='zapisz', command=lambda: MyFunc.save_entry_to_settings(self.entries_content))
        self.save_button.grid(row=2, column=0, padx=5, pady=5, sticky=(W, E))

        self.run_button = Button(self.content_frame, text='uruchom', command=lambda: threading.Thread(target=self.run, name='main_function', daemon=True).start())
        self.run_button.grid(row=3, column=0, padx=5, pady=5, sticky=(W, E))

        # Other things
        MyFunc.fill_entry_from_settings(self.entries_content)

        for list in self.elements_state:
            MyFunc.change_state_on_settings_load(*list)        

        self.master.attributes('-alpha', 1.0)
        self.master.withdraw()          
    
    def hide(self):
        self.master.attributes('-alpha', 0.0)
        self.master.overrideredirect(False)
        self.master.iconify()
        def show(event=None):
            self.master.overrideredirect(True)
            self.master.attributes('-alpha', 1.0)
        self.minimize_button.bind("<Map>", show)    

    def check_groups(self):

        self.farm_group.set('updating...')
        self.gathering_group.set('updating...')
        MyFunc.save_entry_to_settings(self.entries_content)
        bot_functions.check_groups(driver, settings, MyFunc.run_driver, *[self.farm_group, self.gathering_group])

    def run(self):
        """Uruchamia całego bota"""

        if self.entries_content['farm_group'].get() == 'Wybierz grupę':
            MyFunc.custom_error(self, 'Nie wybrano grupy wiosek do farmienia.')
            return

        if self.entries_content['gathering_group'].get() == 'Wybierz grupę':
            MyFunc.custom_error(self, 'Nie wybrano grupy wiosek do zbieractwa.')
            return

        settings_by_worlds = {}
        self.to_do = []

        incoming_attacks = False
        logged = False

        MyFunc.save_entry_to_settings(self.entries_content)
        MyFunc.run_driver()

        for settings_file_name in os.listdir('settings'):
            world_number = settings_file_name[:settings_file_name.find('.')]
            settings_by_worlds[world_number] = MyFunc.load_settings(f'settings//{settings_file_name}')
        
        for world_number in settings_by_worlds:          
            _settings = settings_by_worlds[world_number]

            if int(_settings['A']['active']) | int(_settings['B']['active']) | int(_settings['C']['active']):
                self.to_do.append({'func': 'auto_farm', 'start_time': time.time(), 'world_number': _settings['world_number']})

            if int(_settings['gathering']['active']):
                self.to_do.append({'func': 'gathering', 'start_time': time.time(), 'world_number': _settings['world_number']})

            if int(_settings['check_incoming_attacks']):
                self.to_do.append({'func': 'check_incoming_attacks', 'start_time': time.time(), 'world_number': _settings['world_number']})
        
            if int(_settings['premium_exchange']):
                self.to_do.append({'func': 'premium_exchange', 'start_time': time.time(), 'world_number': _settings['world_number']})

        while True:
            try:                
                if self.to_do[0]['start_time'] < time.time():
                    _settings = settings_by_worlds[self.to_do[0]['world_number']]
                    try:                 
                        if not logged:
                            logged = bot_functions.log_in(driver, _settings)

                        match self.to_do[0]['func']:

                            case 'auto_farm':
                                bot_functions.auto_farm(driver, _settings)
                                self.to_do[0]['start_time'] = time.time() + int(_settings['farm_sleep_time']) * 60
                                self.to_do.append(self.to_do[0])

                            case 'gathering':
                                incoming_attacks = False
                                if int(_settings['gathering']['stop_if_incoming_attacks']):
                                    incoming_attacks = bot_functions.attacks_labels(driver)
                                if not int(_settings['gathering']['stop_if_incoming_attacks']) or (int(_settings['gathering']['stop_if_incoming_attacks']) and not incoming_attacks):
                                    list_of_dicts = bot_functions.gathering_resources(driver, _settings, **self.to_do[0])
                                    for _dict in list_of_dicts:
                                        self.to_do.append(_dict)

                            case 'check_incoming_attacks':
                                bot_functions.attacks_labels(driver, int(_settings['email_notifications']))
                                self.to_do[0]['start_time'] = time.time() + int(_settings['check_incoming_attacks_sleep_time']) * 60
                                self.to_do.append(self.to_do[0])

                            case 'premium_exchange':
                                bot_functions.premium_exchange(driver, _settings)
                                self.to_do[0]['start_time'] = time.time() + random.uniform(5, 8) * 60
                                self.to_do.append(self.to_do[0])

                            case 'build':
                                pass
                        
                        del self.to_do[0]
                        # Aktualizacja listy zadań jeśli okno zadań jest aktualnie wyświetlone 
                        if hasattr(self, 'jobs_info'):
                            if hasattr(self.jobs_info, 'master'):
                                if self.jobs_info.master.winfo_exists():
                                    self.jobs_info.print_jobs()
                        self.to_do.sort(key=lambda sort_by: sort_by['start_time'])

                    except BaseException:                        
                        html = driver.page_source
                        if html.find('chat-disconnected') != -1 or 'session_expired' in driver.current_url:
                            logged = bot_functions.log_in(driver, _settings)
                            if logged:
                                continue
                            else:
                                driver.quit()
                                MyFunc.run_driver()
                                logged = bot_functions.log_in(driver, _settings)
                                continue
                            
                        if bot_functions.unwanted_page_content(driver, html):
                            continue
                        else:
                            driver.quit()
                            MyFunc.run_driver()
                            logged = bot_functions.log_in(driver, _settings)
                            continue

                    # Zamyka stronę plemion jeśli do następnej czynności pozostało więcej niż 5min
                    if self.to_do[0]['start_time'] > time.time() + 300 or _settings['world_number'] != self.to_do[0]['world_number']:
                        driver.get('chrome://newtab')
                        logged = False

                # Uruchamia timer w oknie głównym i oknie zadań (jeśli istnieje)
                for _ in range(int(self.to_do[0]['start_time']-time.time()), 0, -1):
                    if hasattr(self, 'jobs_info'):
                        if hasattr(self.jobs_info, 'master'):
                            if self.jobs_info.master.winfo_exists():
                                self.jobs_info.time.set(f'{datetime.timedelta(seconds=_)}')
                    self.time.set(f'{datetime.timedelta(seconds=_)}')                    
                    time.sleep(1)
                if hasattr(self, 'jobs_info'):
                        if hasattr(self.jobs_info, 'master'):
                            if self.jobs_info.master.winfo_exists():
                                self.jobs_info.time.set('Running..')
                self.time.set('Running..')

            except BaseException:
                bot_functions.log_error(driver)

    def add_new_world_settings(self):
        global settings
        
        entries_world = self.entries_content['world_number'].get()

        if os.path.exists(f'settings/{entries_world}.json'):
            MyFunc().custom_error('Ustawienia tego świata już istnieją!')
        else:
            if not os.path.isdir('settings'):
                os.mkdir('settings')
            # Ustawia domyślne wartości elementów GUI (entries_content)
            for key in self.entries_content:
                if isinstance(settings[key], dict):
                    for key_ in settings[key]:
                        if isinstance(settings[key][key_], dict):
                            for _key_ in settings[key][key_]:
                                if isinstance(settings[key][key_][_key_], dict):
                                    for __key__ in settings[key][key_][_key_]:
                                        self.entries_content[key][key_][_key_][__key__].set(value='')                                                
                                else:
                                    self.entries_content[key][key_][_key_].set(value='')                                    
                        else:
                            self.entries_content[key][key_].set(value='')                        
                else:
                    self.entries_content[key].set(value='')
            self.entries_content['world_number'].set(value=entries_world)
            MyFunc.save_entry_to_settings(self.entries_content)
            self.entries_content['world_in_title'].set(f'PL{entries_world}')

    def show_world_chooser_window(self, event) -> None:
        """Show new window with available worlds settings to choose"""

        def change_world(world_number: str) -> None:
            global settings

            if os.path.exists(f'settings/{world_number}.json'):
                # Save current settings before changing to other
                MyFunc.save_entry_to_settings(self.entries_content)
                settings = MyFunc.load_settings(f'settings/{world_number}.json')
                MyFunc.fill_entry_from_settings(self.entries_content)
                for list in self.elements_state:
                    MyFunc.change_state_on_settings_load(*list)
                self.entries_content['world_in_title'].set(f'PL{world_number}')
                self.world_chooser_window.destroy()

        def on_leave(event) -> None:
            if event.widget != self.world_chooser_window:
                return

            def on_enter(event) -> None:
                if event.widget != self.world_chooser_window:
                    return
                main_window.master.unbind('<Button-1>', self.btn_func_id)
                
            def quit(event) -> None:
                main_window.master.unbind('<Button-1>', self.btn_func_id)
                self.world_chooser_window.destroy()

            self.btn_func_id = main_window.master.bind('<Button-1>', quit, '+')
            self.world_chooser_window.bind('<Enter>', on_enter)

        self.world_chooser_window = Toplevel(self.title_world, borderwidth=1, relief='groove')
        self.world_chooser_window.attributes('-alpha', 0.0)
        self.world_chooser_window.overrideredirect(True)
        self.world_chooser_window.attributes('-topmost', 1) 
        
        # Creat new style for buttons in world_chooser_window
        style.configure('test.Link.TButton', foreground='white')
        style.map('test.Link.TButton', background=[('active', '#333333')], foreground=[('active', 'white')])

        # for color_label in style.colors.label_iter():
        #     print(style.colors.get(color_label))

        for index, settings_file_name in enumerate(os.listdir('settings')):
            world_number = settings_file_name[:settings_file_name.find('.')]
            Button(self.world_chooser_window, style='test.Link.TButton', text=f'PL{world_number}', command=partial(change_world, world_number)).grid(row=index, column=0)

        self.world_chooser_window.bind('<Leave>', on_leave)
        MyFunc.center(self.world_chooser_window, self.title_world)
        self.world_chooser_window.attributes('-alpha', 1.0)

    def show_jobs_to_do_window(self, event) -> None:
        
        if hasattr(self, 'jobs_info'):
            if hasattr(self.jobs_info, 'master'):
                if self.jobs_info.master.winfo_exists():
                    self.jobs_info.master.deiconify()
                    MyFunc.center(self.jobs_info.master, main_window.master)
                else:
                    self.jobs_info = JobsToDoWindow()
                return

        self.jobs_info = JobsToDoWindow()


class LogInWindow:

    def __init__(self) -> None:
        settings['logged'] = False
        if 'user_password' in settings:
            with DataBaseConnection() as cursor:            
                cursor.execute("SELECT * FROM Konta_Plemiona WHERE UserName='" 
                                + settings['user_name'] 
                                + "' AND Password='" 
                                + settings['user_password']
                                + "'")
                row = cursor.fetchone()
                if not row:
                    MyFunc().custom_error('Automatyczne logowanie nie powiodło się.')
                elif not MyFunc.if_paid(str(row[5])):
                    MyFunc().custom_error('Ważność konta wygasła.')                
                elif row[6]:
                    MyFunc().custom_error('Konto jest już obecnie w użyciu.')                
                else:                    
                    main_window.master.deiconify()
                    MyFunc.center(main_window.master)
                    settings['logged'] = True
                    return
        
        self.master = Toplevel(borderwidth=1, relief='groove')
        self.master.overrideredirect(True)
        self.master.resizable(0, 0)
        self.master.attributes('-topmost', 1)
        
        self.custom_bar = Frame(self.master)
        self.custom_bar.grid(row=0, column=0, sticky=(N, S, E, W))
        self.custom_bar.columnconfigure(3, weight=1)

        self.title_label = Label(self.custom_bar, text='Logowanie')
        self.title_label.grid(row=0, column=2, padx=5 , sticky=W)

        self.exit_button = Button(self.custom_bar, text='X', command=main_window.master.destroy)
        self.exit_button.grid(row=0, column=4, padx=(0, 5), pady=3, sticky=E)

        Separator(self.master, orient=HORIZONTAL).grid(row=1, column=0, sticky=(W, E))
        
        self.content = Frame(self.master)
        self.content.grid(row=2, column=0, sticky=(N, S, E, W))

        self.user_name = Label(self.content, text='Nazwa:')
        self.user_password = Label(self.content, text='Hasło:')
        self.register = Label(self.content, text='Nie posiadasz jeszcze konta?')

        self.user_name.grid(row=2, column=0, pady=4, padx=5, sticky='W')
        self.user_password.grid(row=3, column=0, pady=4, padx=5, sticky='W')
        self.register.grid(row=6, column=0, columnspan=2, pady=(4, 0), padx=5)

        self.user_name_input = Entry(self.content)
        self.user_password_input = Entry(self.content, show='*')

        self.user_name_input.grid(row=2, column=1, pady=(5, 5), padx=5)
        self.user_password_input.grid(row=3, column=1, pady=4, padx=5)

        self.remember_me = StringVar()
        self.remember_me_button = Checkbutton(self.content, text='Zapamiętaj mnie', 
                                         variable=self.remember_me, onvalue=True, offvalue=False)
        self.remember_me_button.grid(row=4, columnspan=2, pady=4, padx=5, sticky='W')

        self.log_in_button = Button(self.content, text='Zaloguj', command=self.log_in)
        self.register_button = Button(self.content, text='Utwórz konto')

        self.log_in_button.grid(row=5, columnspan=2, pady=4, padx=5, sticky=(W, E))
        self.register_button.grid(row=7, columnspan=2, pady=5, padx=5, sticky=(W, E))

        self.user_name_input.focus()
        self.user_password_input.bind('<Return>', self.log_in)
        self.custom_bar.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'custom_bar'))
        self.title_label.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'title_label'))

        MyFunc.center(self.master)
    
    def log_in(self, event=None):
        with DataBaseConnection() as cursor:            
            cursor.execute("SELECT * FROM Konta_Plemiona WHERE UserName='" 
                            + self.user_name_input.get() 
                            + "' AND Password='" 
                            + self.user_password_input.get() 
                            + "'")
            row = cursor.fetchone()
            if not row:                
                MyFunc().custom_error('Wprowadzono nieprawidłowe dane')
                return
            if not MyFunc.if_paid(str(row[5])):
                MyFunc().custom_error('Ważność konta wygasła')
                return
            if row[6]:
                MyFunc().custom_error('Konto jest już obecnie w użyciu')
                return
            settings['logged'] = True

        if settings['logged']:
            if self.remember_me.get():
                settings['user_name'] = self.user_name_input.get()
                settings['user_password'] = self.user_password_input.get()
                with open('settings.json', 'w') as settings_json_file:
                    json.dump(settings, settings_json_file)
            
            self.master.destroy() 
            main_window.master.deiconify()
            MyFunc.center(main_window.master)


class JobsToDoWindow:   

    translate_tuples = (
            ('gathering', 'zbieractwo'),
            ('auto_farm', 'farmienie'),
            ('check_incoming_attacks', 'etykiety ataków'),
            ('premium_exchange', 'giełda premium')
        )

    def __init__(self) -> None:        
        self.master = Toplevel()
        self.master.attributes('-alpha', 0.0)
        self.master.iconbitmap(default='icons//ikona.ico')        
        self.master.title('Tribal Wars 24/7')        
        self.master.overrideredirect(True)
        self.master.attributes('-topmost', 1)

        # main_frame -> custom_bar, content_frame
        self.main_frame = Frame(self.master, borderwidth=1, relief='groove')
        self.main_frame.grid(row=0, column=0, sticky=(N, S, E, W))

        self.custom_bar = Frame(self.main_frame)
        self.custom_bar.grid(row=0, column=0, sticky=(N, S, E, W))
        self.custom_bar.columnconfigure(3, weight=1)

        self.content_frame = Frame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky=(N, S, E, W))

        # custom_bar
        self.title_label = Label(self.custom_bar, text='Lista zadań')
        self.title_label.grid(row=0, column=1, padx=(5, 0) , sticky=W)

        self.time = StringVar()
        self.title_timer = Label(self.custom_bar, textvariable=self.time)
        self.title_timer.grid(row=0, column=2, padx=5)

        self.photo = PhotoImage(file='icons//minimize.png')
        self.minimize = self.photo.subsample(2, 2)

        self.minimize_button = Button(self.custom_bar, style='primary.Link.TButton', image=self.minimize, command=self.hide)
        self.minimize_button.grid(row=0, column=4, padx=(5, 0), pady=5, sticky=E)

        self.photo = PhotoImage(file='icons//exit.png')
        self.exit = self.photo.subsample(8, 8)

        self.exit_button = Button(self.custom_bar, style='primary.Link.TButton', image=self.exit, command=self.master.destroy)
        self.exit_button.grid(row=0, column=5, padx=(0, 5), pady=3, sticky=E)      

        self.custom_bar.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'custom_bar'))
        self.title_label.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'title_label'))
        self.title_timer.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'title_timer'))

        # content_frame

        self.print_jobs()

        MyFunc.center(self.master, main_window.master)        
        self.time.set(f'{datetime.timedelta(seconds=int(main_window.to_do[0]["start_time"] - time.time()))}')
        self.master.attributes('-alpha', 1.0)

    def hide(self):        
        self.master.attributes('-alpha', 0.0)
        self.master.overrideredirect(False)
        self.master.iconify()
        def show(event=None):
            self.master.overrideredirect(True)
            self.master.attributes('-alpha', 1.0)
        self.minimize_button.bind("<Map>", show)    

    def print_jobs(self):   
        
        def on_configure(event):
            # Update scrollregion after starting 'mainloop'
            # when all widgets are in canvas.
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))

        def _bound_to_mousewheel(self, event):
            self.canvas.bind_all("<MouseWheel>", lambda event: _on_mousewheel(self, event))

        def _unbound_to_mousewheel(self, event):
            self.canvas.unbind_all("<MouseWheel>")

        def _on_mousewheel(self, event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        # --- Create self.canvas with scrollbar ---

        self.canvas = Canvas(self.content_frame)
        self.canvas.grid(row=0, column=0, sticky=NSEW)

        self.scrollbar = Scrollbar(self.content_frame, command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky=NS)

        self.canvas.configure(yscrollcommand = self.scrollbar.set)
        self.canvas.bind('<Enter>', lambda event: _bound_to_mousewheel(self, event))
        self.canvas.bind('<Leave>', lambda event: _unbound_to_mousewheel(self, event))

        # Update scrollregion after starting 'mainloop'
        # when all widgets are in self.canvas.
        self.canvas.bind('<Configure>', on_configure)

        # --- Put frame in self.canvas ---

        self.frame = Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.frame)

        # --- Add widgets in self.frame ---      
        self.add_widgets_to_frame()
    
    def add_widgets_to_frame(self) -> None:
        """Add widgets to self.frame in self.canvas"""
        
        # Table description -> column names
        for col_index, col_name in zip(range(1, 4, 1), ('Świat', 'Zadanie', 'Data wykonania')):
            if col_name != 'Data wykonania':
                Label(self.frame, text=col_name).grid(row=0, column=col_index, padx=10, pady=5)                
            else:
                Label(self.frame, text=col_name).grid(row=0, column=col_index, padx=(10, 25), pady=5)                  
        
        # Create table with data of jobs to do
        for row_index, row in enumerate(main_window.to_do):  
            row_index += 1                    
            Label(self.frame, text=f'{row_index}.').grid(row=row_index, column=0, padx=(25, 10), pady=5)            
            for col_index, col in enumerate(('world_number', 'func', 'start_time')):
                match col:
                    case 'func':
                        for search_for, change_to in self.translate_tuples:
                            if row[col] == search_for:
                                label_text = change_to
                    case 'start_time':
                        label_text = time.strftime('%H:%M:%S %d.%m.%Y', time.localtime(row[col]))
                    case _:
                        label_text = str(row[col])
                if col != 'start_time':
                    Label(self.frame, text=label_text).grid(row=row_index, column=col_index+1, padx=10, pady=5)                    
                else:
                    Label(self.frame, text=label_text).grid(row=row_index, column=col_index+1, padx=(10, 25), pady=(5, 10))                    

        # Update canvas size depend on frame requested size
        self.frame.update()
        if self.frame.winfo_reqheight() <= 250:
            self.canvas['height'] = self.frame.winfo_reqheight()
        else:
            self.canvas['height'] = 250
        self.canvas['width'] = self.frame.winfo_reqwidth()

        self.canvas.yview_moveto(0)

    def update_widgets_in_frame(self) -> None:
        """Clear and than create new widgets in frame"""

        for widgets in self.frame.winfo_children():
            widgets.destroy()            
        self.add_widgets_to_frame()


if __name__ == '__main__':    

    driver = None
    settings = MyFunc.load_settings()

    if settings['first_lunch']:
        MyFunc.first_app_lunch()

    main_window = MainWindow()
    style = Style(theme='darkly')
    style.map('primary.Link.TButton', background=[('active', 'gray18')], bordercolor=[('active', '')])
    style.theme_use()
    log_in_window = LogInWindow()

    main_window.master.mainloop()