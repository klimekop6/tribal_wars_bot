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
import tkinter as tk
from functools import partial
from math import sqrt

import pyodbc
import requests
import ttkbootstrap as ttk
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

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

        driver = webdriver.Chrome(service=Service(ChromeDriverManager(cache_valid_range=31).install()))
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

    def custom_error(self, message: str, auto_hide: bool=False, parent=None) -> None:
        
        self.master = tk.Toplevel(borderwidth=1, relief='groove')
        self.master.overrideredirect(True)
        self.master.attributes('-topmost', 1)        
        self.master.bell()

        if not auto_hide:
            self.message_label = ttk.Label(self.master, text=message)
            self.message_label.grid(row=1, column=0, padx=5, pady=5)

            self.ok_button = ttk.Button(self.master, text='ok', command=self.master.destroy)
            self.ok_button.grid(row=2, column=0, pady=(5,8))
        
            self.message_label.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'message_label'))
            self.ok_button.focus_force()
            self.ok_button.bind('<Return>', lambda event: self.master.destroy())

        if auto_hide:
            self.message_label = ttk.Label(self.master, text=message)
            self.message_label.grid(row=1, column=0, padx=10, pady=8)
            self.master.after(ms=2000, func=lambda: self.master.destroy())

        MyFunc.center(self.master, parent=parent)

    def fill_entry_from_settings(entries: dict) -> None:

        for key in entries:
            if key in settings:
                if settings[key]:
                    if isinstance(settings[key], dict):
                        for key_ in settings[key]:
                            if key_ not in entries[key]:
                                continue
                            if settings[key][key_]:
                                if isinstance(settings[key][key_], dict):
                                    for _key_ in settings[key][key_]:
                                        if _key_ not in entries[key][key_]:
                                            continue
                                        if settings[key][key_][_key_]:
                                            if isinstance(settings[key][key_][_key_], dict):
                                                for __key__ in settings[key][key_][_key_]:
                                                    if __key__ not in entries[key][key_][_key_]:
                                                        continue                                                    
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
                return webdriver.Chrome(service=Service(ChromeDriverManager(cache_valid_range=31).install()), options=chrome_options)
            else:
                chrome_options = Options()
                chrome_options.add_argument('user-data-dir=' + settings['path'])
                chrome_options.add_extension(extension='0.60_0.crx')
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
                while True:
                    try:   
                        driver = webdriver.Chrome(service=Service(ChromeDriverManager(cache_valid_range=31).install()), options=chrome_options)
                        break
                    except:
                        time.sleep(10)
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

        if not settings['world_number'] or settings['world_number'] == '0':
            return

        if not os.path.isdir('settings'):
            os.mkdir('settings')

        with open(f'settings/{settings["world_number"]}.json', 'w') as settings_json_file:
            json.dump(settings, settings_json_file)


class ScrollableFrame:
    """Create scrollable frame on top of canvas"""

    def __init__(self, parent=None) -> None:

        self.parent = parent

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
        
        self.canvas = tk.Canvas(parent)
        self.canvas.grid(row=0, column=0, sticky=tk.NSEW)

        self.scrollbar = ttk.Scrollbar(parent, command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky=tk.NS)

        self.canvas.configure(yscrollcommand = self.scrollbar.set)
        self.canvas.bind('<Enter>', lambda event: _bound_to_mousewheel(self, event))
        self.canvas.bind('<Leave>', lambda event: _unbound_to_mousewheel(self, event))

        # Update scrollregion after starting 'mainloop'
        # when all widgets are in self.canvas.
        self.canvas.bind('<Configure>', on_configure)

        # --- Put frame in self.canvas ---

        self.frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.frame, anchor=tk.NW)

    def update_canvas(self, max_height: int=500) -> None:
        """Update canvas size depend on frame requested size"""

        self.frame.update_idletasks()
        if self.frame.winfo_reqheight() <= max_height:
            self.canvas['height'] = self.frame.winfo_reqheight()
        else:
            self.canvas['height'] = max_height
        self.canvas['width'] = self.frame.winfo_reqwidth()

        self.frame.update_idletasks()
        self.canvas.yview_moveto(0)


class NotebookSchedul:
    """Content and functions to put in notebook frame f3 named 'Planer'."""

    def __init__(self, parent: tk.Widget, entries_content: dict) -> None:

        self.parent = parent
        self.entries_content = entries_content

        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

        photo = tk.PhotoImage(file='icons//minimize.png')
        self.minus = photo.subsample(2, 2)
        photo = tk.PhotoImage(file='icons//plus.png')
        self.plus = photo.subsample(2, 2) 
        photo = tk.PhotoImage(file='icons//exit.png')
        self.exit = photo.subsample(8, 8) 

        entries_content['scheduler'] = {}

        self.scroll_able = ScrollableFrame(parent)

        ttk.Label(self.scroll_able.frame, text='Data wejścia wojsk').grid(row=0, column=0, columnspan=2, padx=5, pady=(10, 5))

        self.destiny_date = ttk.DateEntry(self.scroll_able.frame, dateformat='%d.%m.%Y %H:%M:%S:%f', firstweekday=0)
        self.destiny_date.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        ttk.Label(self.scroll_able.frame, text='Wioski startowe').grid(row=3, column=0, padx=5, pady=10)
        ttk.Label(self.scroll_able.frame, text='Wioski docelowe').grid(row=3, column=1, padx=5, pady=10)

        self.villages_to_use = tk.Text(self.scroll_able.frame, wrap='word', height=5, width=28)
        self.villages_to_use.grid(row=4, column=0, padx=5, pady=(0, 5))
        self.villages_destiny = tk.Text(self.scroll_able.frame, wrap='word', height=5, width=28)
        self.villages_destiny.grid(row=4, column=1, padx=5, pady=(0, 5))

        # Rodzaj komendy -> atak lub wsparcie
        ttk.Label(self.scroll_able.frame, text='Rodzaj komendy').grid(row=5, column=0, columnspan=2, padx=5, pady=(10, 5), sticky=tk.W)
        self.command_type = tk.StringVar()
        self.command_type_attack = ttk.Radiobutton(self.scroll_able.frame, text='Atak', value='target_attack', variable=self.command_type)
        self.command_type_attack.grid(row=6, column=0, padx=(25, 5), pady=5, sticky=tk.W)
        self.command_type_support = ttk.Radiobutton(self.scroll_able.frame, text='Wsparcie', value='target_support', variable=self.command_type)
        self.command_type_support.grid(row=7, column=0, padx=(25, 5), pady=5, sticky=tk.W)        

        # Szablon wojsk        
        ttk.Label(self.scroll_able.frame, text='Szablon wojsk').grid(row=8, column=0, padx=5, pady=(10, 5), sticky=tk.W)

        # Wyślij wszystkie
        self.template_type = tk.StringVar()
        self.all_troops_radiobutton = ttk.Radiobutton(
            self.scroll_able.frame, text='Wyślij wszystkie', 
            value='send_all', variable=self.template_type,
            command=lambda: [
                self.choosed_fake_template.set(''),
                self.choose_slowest_troop.config(state='readonly')
                ]
            )
        self.all_troops_radiobutton.grid(row=9, column=0, columnspan=2, padx=(25, 5), pady=5, sticky=tk.W)

        self.army_type = tk.StringVar()  # Wysłać jednostki off czy deff
        self.only_off_radiobutton = ttk.Radiobutton(
            self.scroll_able.frame, 
            text='Wyślij tylko jednostki offensywne',
            value='only_off', variable=self.army_type,
            command=lambda: self.all_troops_radiobutton.invoke()
            )
        self.only_off_radiobutton.grid(row=14, column=0, columnspan=2, padx=(45, 5), pady=5, sticky=tk.W)
        
        self.only_deff_radiobutton = ttk.Radiobutton(
            self.scroll_able.frame, 
            text='Wyślij tylko jednostki deffensywne',
            value='only_deff', variable=self.army_type,
            command=lambda: self.all_troops_radiobutton.invoke()
            )
        self.only_deff_radiobutton.grid(row=15, column=0, columnspan=2, padx=(45, 5), pady=5, sticky=tk.W)

        self.send_snob = tk.StringVar()  # Czy wysłać szlachtę
        self.no_snob_radiobutton = ttk.Radiobutton(
            self.scroll_able.frame, 
            text='Nie wysyłaj szlachty',
            value='no_snob', variable=self.send_snob,
            command=lambda: [
                self.all_troops_radiobutton.invoke(),
                self.snob_amount_entry.config(state='disabled'),
                self.first_snob_army_size_entry.config(state='disabled'),
                self.slowest_troop.set('Taran')
                ]
            )
        self.no_snob_radiobutton.grid(row=10, column=0, columnspan=2, padx=(45, 5), pady=5, sticky=tk.W)
        
        self.send_snob_radiobutton = ttk.Radiobutton(
            self.scroll_able.frame, text='Wyślij szlachtę',
            value='send_snob', variable=self.send_snob,
            command=lambda: [
                self.all_troops_radiobutton.invoke(),
                self.snob_amount_entry.config(state='normal'),
                self.first_snob_army_size_entry.config(state='normal'),
                self.slowest_troop.set('Szlachcic')
                ]
            )
        self.send_snob_radiobutton.grid(row=11, column=0, columnspan=2, padx=(45, 5), pady=5, sticky=tk.W)   

        ttk.Label(self.scroll_able.frame, text='Liczba szlachiców').grid(row=12, column=0, columnspan=2, padx=(65, 5), pady=(5, 0), sticky=tk.W)
        self.snob_amount = tk.StringVar()  # Ile grubych wysłać
        self.snob_amount_entry = ttk.Entry(self.scroll_able.frame, textvariable=self.snob_amount, width=4, justify=tk.CENTER, state='disabled')
        self.snob_amount_entry.grid(row=12, column=0, columnspan=2, padx=(5, 25), pady=(5, 0), sticky=tk.E)

        ttk.Label(self.scroll_able.frame, text='Obstawa pierwszego szlachcica [%]').grid(row=13, column=0, columnspan=2, padx=(65, 5), pady=5, sticky=tk.W)
        self.first_snob_army_size = tk.StringVar()  # Wielkość obstawy pierwszego grubego wyrażona w %
        self.first_snob_army_size_entry = ttk.Entry(self.scroll_able.frame, textvariable=self.first_snob_army_size, width=4, justify=tk.CENTER, state='disabled')
        self.first_snob_army_size_entry.grid(row=13, column=0, columnspan=2, padx=(5, 25), pady=5, sticky=tk.E)        

        ttk.Label(self.scroll_able.frame, text='Najwolniejsza jednostka').grid(row=16, column=0, columnspan=2, padx=(45, 5), pady=5, sticky=tk.W)
        self.slowest_troop = tk.StringVar()
        ttk.Combobox(self.scroll_able.frame)  # For nothing :D
        self.choose_slowest_troop = ttk.Combobox(
            self.scroll_able.frame, 
            textvariable=self.slowest_troop, 
            width=14,
            justify=tk.CENTER
        )
        self.choose_slowest_troop.grid(row=16, column=0, columnspan=2, padx=(5, 25), pady=5, sticky=tk.E)
        self.choose_slowest_troop['state'] = 'readonly'
        self.choose_slowest_troop['values'] = (
            'Pikinier', 
            'Miecznik', 
            'Topornik', 
            'Łucznik', 
            'Zwiadowca', 
            'Lekka kawaleria', 
            'Łucznik konny', 
            'Ciężka kawaleria', 
            'Taran', 
            'Katapulta',
            'Rycerz',
            'Szlachcic'
        )

        # Wyślij fejki
        self.fake_troops_radiobutton = ttk.Radiobutton(
            self.scroll_able.frame, text='Wyślij fejki', 
            value='send_fake', variable=self.template_type,
            command=lambda: [
                self.send_snob.set(''), 
                self.snob_amount_entry.config(state='disabled'),
                self.first_snob_army_size_entry.config(state='disabled'),
                self.army_type.set(''),
                self.slowest_troop.set(''),
                self.choose_slowest_troop.config(state='disabled')
                ]
            )
        self.fake_troops_radiobutton.grid(row=17, column=0, columnspan=2, padx=(25, 5), pady=5, sticky=tk.W)

        ttk.Label(self.scroll_able.frame, text='Dostępne szablony').grid(row=18, column=0, columnspan=2, padx=(45, 5), pady=5, sticky=tk.W)
        
        settings.setdefault('scheduler', {})
        settings['scheduler'].setdefault('fake_templates', {})
        self.choosed_fake_template = tk.StringVar()  # Wybrany szablon
        self.available_templates()  # Wyświetla dostępne szablony stworzone przez użytkownika

        ttk.Button(self.scroll_able.frame, image=self.plus, bootstyle='primary.Link.TButton', command=self.create_template).grid(row=18, column=0, columnspan=2, padx=(0, 27), pady=5, sticky=tk.E)

        # Własny szablon
        self.own_template_radiobutton = ttk.Radiobutton(
            self.scroll_able.frame, text='Własny szablon', 
            value='send_my_template', variable=self.template_type,
            command=lambda: [
                self.send_snob.set(''), 
                self.snob_amount_entry.config(state='disabled'),
                self.first_snob_army_size_entry.config(state='disabled'),
                self.army_type.set(''),
                self.slowest_troop.set(''),
                self.choosed_fake_template.set(''),
                self.choose_slowest_troop.config(state='disabled')
                ]
            )
        self.own_template_radiobutton.grid(row=41, column=0, columnspan=2, padx=(25, 5), pady=10, sticky=tk.W)

        army_frame = ttk.Frame(self.scroll_able.frame)
        army_frame.grid(row=42, column=0, columnspan=2, sticky=tk.EW)

        army_frame.columnconfigure(0, weight=11)
        army_frame.columnconfigure(1, weight=11)
        army_frame.columnconfigure(2, weight=10)
        army_frame.columnconfigure(3, weight=10)

        self.spear_photo = tk.PhotoImage(file='icons//spear.png')
        ttk.Label(army_frame, image=self.spear_photo).grid(row=0, column=0, padx=(25, 0), pady=(5, 0), sticky=tk.W)

        self.spy_photo = tk.PhotoImage(file='icons//spy.png')
        ttk.Label(army_frame, image=self.spy_photo).grid(row=0, column=1, padx=(25, 0), pady=(5, 0), sticky=tk.W)

        self.ram_photo = tk.PhotoImage(file='icons//ram.png')
        ttk.Label(army_frame, image=self.ram_photo).grid(row=0, column=2, padx=(21, 0), pady=(5, 0), sticky=tk.W)

        self.knight_photo = tk.PhotoImage(file='icons//knight.png')
        ttk.Label(army_frame, image=self.knight_photo).grid(row=0, column=3, padx=(21, 0), pady=(5, 0), sticky=tk.W)

        self.sword_photo = tk.PhotoImage(file='icons//sword.png')
        ttk.Label(army_frame, image=self.sword_photo).grid(row=1, column=0, padx=(25, 0), pady=(5, 0), sticky=tk.W)

        self.light_photo = tk.PhotoImage(file='icons//light.png')
        ttk.Label(army_frame, image=self.light_photo).grid(row=1, column=1, padx=(25, 0), pady=(5, 0), sticky=tk.W)
        
        self.catapult_photo = tk.PhotoImage(file='icons//catapult.png')
        ttk.Label(army_frame, image=self.catapult_photo).grid(row=1, column=2, padx=(21, 0), pady=(5, 0), sticky=tk.W)
        
        self.snob_photo = tk.PhotoImage(file='icons//snob.png')
        ttk.Label(army_frame, image=self.snob_photo).grid(row=1, column=3, padx=(21, 0), pady=(5, 0), sticky=tk.W)
        
        self.axe_photo = tk.PhotoImage(file='icons//axe.png')
        ttk.Label(army_frame, image=self.axe_photo).grid(row=2, column=0, padx=(25, 0), pady=(5, 0), sticky=tk.W)
     
        self.marcher_photo = tk.PhotoImage(file='icons//marcher.png')
        ttk.Label(army_frame, image=self.marcher_photo).grid(row=2, column=1, padx=(25, 0), pady=(5, 0), sticky=tk.W)
       
        self.archer_photo = tk.PhotoImage(file='icons//archer.png')
        ttk.Label(army_frame, image=self.archer_photo).grid(row=3, column=0, padx=(25, 0), pady=(5, 5), sticky=tk.W)

        self.heavy_photo = tk.PhotoImage(file='icons//heavy.png')
        ttk.Label(army_frame, image=self.heavy_photo).grid(row=3, column=1, padx=(25, 0), pady=(5, 5), sticky=tk.W)

        self.troops = {
            'spear':    tk.StringVar(),
            'sword':    tk.StringVar(),
            'axe':      tk.StringVar(),
            'archer':   tk.StringVar(),
            'spy':      tk.StringVar(),
            'light':    tk.StringVar(),
            'marcher':  tk.StringVar(),
            'heavy':    tk.StringVar(),
            'ram':      tk.StringVar(),
            'catapult': tk.StringVar(),
            'knight':   tk.StringVar(),
            'snob':     tk.StringVar()
        }

        ttk.Entry(army_frame, width=5, textvariable=self.troops['spear']).grid(row=0, column=0, padx=(0, 0), pady=(5, 0), sticky=tk.E)
        ttk.Entry(army_frame, width=5, textvariable=self.troops['spy']).grid(row=0, column=1, padx=(0, 3), pady=(5, 0), sticky=tk.E)
        ttk.Entry(army_frame, width=5, textvariable=self.troops['ram']).grid(row=0, column=2, padx=(0, 0), pady=(5, 0), sticky=tk.E)
        ttk.Entry(army_frame, width=5, textvariable=self.troops['knight']).grid(row=0, column=3, padx=(0, 25), pady=(5, 0), sticky=tk.E)
        ttk.Entry(army_frame, width=5, textvariable=self.troops['sword']).grid(row=1, column=0, padx=(0, 0), pady=(5, 0), sticky=tk.E)
        ttk.Entry(army_frame, width=5, textvariable=self.troops['light']).grid(row=1, column=1, padx=(0, 3), pady=(5, 0), sticky=tk.E)
        ttk.Entry(army_frame, width=5, textvariable=self.troops['catapult']).grid(row=1, column=2, padx=(0, 0), pady=(5, 0), sticky=tk.E)
        ttk.Entry(army_frame, width=5, textvariable=self.troops['snob']).grid(row=1, column=3, padx=(0, 25), pady=(5, 0), sticky=tk.E)
        ttk.Entry(army_frame, width=5, textvariable=self.troops['axe']).grid(row=2, column=0, padx=(0, 0), pady=(5, 0), sticky=tk.E)
        ttk.Entry(army_frame, width=5, textvariable=self.troops['marcher']).grid(row=2, column=1, padx=(0, 3), pady=(5, 0), sticky=tk.E)
        ttk.Entry(army_frame, width=5, textvariable=self.troops['archer']).grid(row=3, column=0, padx=(0, 0), pady=(5, 5), sticky=tk.E)
        ttk.Entry(army_frame, width=5, textvariable=self.troops['heavy']).grid(row=3, column=1, padx=(0, 3), pady=(5, 5), sticky=tk.E)      

        settings['scheduler'].setdefault('ready_schedule', [])
        if settings['scheduler']['ready_schedule']:
            current_time = time.time()
            settings['scheduler']['ready_schedule'] = [
                value for value in settings['scheduler']['ready_schedule'] 
                if value['send_time'] > current_time
                ]

        self.add_to_schedule = ttk.Button(self.scroll_able.frame, text='Dodaj do planera [F5]', command=self.create_schedule)
        self.add_to_schedule.grid(row=43, columnspan=2, pady=10)

        self.scroll_able.frame.bind_all('<F5>', lambda _: self.add_to_schedule.invoke())

        # Update canvas size depend on frame requested size
        self.scroll_able.update_canvas(max_height=500)

    def available_templates(self) -> None:

        def delete_template(row_number, template_name):             
            del settings['scheduler']['fake_templates'][template_name]
            self.forget_row(self.scroll_able.frame, row_number)
            self.scroll_able.frame.update_idletasks()
            self.scroll_able.canvas.configure(scrollregion=self.scroll_able.canvas.bbox('all'))

        if not settings['scheduler']['fake_templates']:
            ttk.Label(
                self.scroll_able.frame, 
                text='Brak dostępnych szablonów'
            ).grid(row=20, column=0, columnspan=2, padx=(65, 5), pady=(0, 5), sticky=tk.W)

        for index, template_name in enumerate(settings['scheduler']['fake_templates']):
            ttk.Radiobutton(
                self.scroll_able.frame, 
                text=f'{template_name}', 
                value=settings["scheduler"]["fake_templates"][template_name], 
                variable=self.choosed_fake_template,
                command=lambda: self.fake_troops_radiobutton.invoke()
            ).grid(row=20+index, column=0, padx=(65, 5), sticky=tk.W)
            ttk.Button(
                self.scroll_able.frame, 
                image=self.exit, 
                bootstyle='primary.Link.TButton',
                command=partial(delete_template, index+20, template_name)
            ).grid(row=20+index, column=0, columnspan=2, padx=(5, 27), sticky=tk.E)

    def create_schedule(self) -> None:
        """Create scheduled defined on used options by the user"""

        def get_villages_id(settings: dict[str], update: bool=False) -> dict:
            """Download, process and save in text file for future use.
            In the end return all villages in the world with proper id.
            """    

            def update_world_villages_file() -> None:
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
                update_world_villages_file()

            villages = {}
            try:
                world_villages_file = open(f'villages{settings["world_number"]}.txt')
            except FileNotFoundError:
                update_world_villages_file()
                world_villages_file = open(f'villages{settings["world_number"]}.txt')
            else:
                for row in world_villages_file:
                    village_coords, village_id = row.split(',')
                    villages[village_coords] = village_id
            finally:
                world_villages_file.close()

            return villages

        arrival_time = self.destiny_date.entry.get()
        sends_from = self.villages_to_use.get('1.0', tk.END)
        sends_to = self.villages_destiny.get('1.0', tk.END)
        command_type = self.command_type.get()
        template_type = self.template_type.get()

        match template_type:
            case 'send_all':        
                army_type = self.army_type.get()
                send_snob = self.send_snob.get()
                if send_snob == 'send_snob':
                    snob_amount = self.snob_amount.get()
                    first_snob_army_size = self.first_snob_army_size.get()

            case 'send_fake':        
                choosed_fake_template = json.loads(self.choosed_fake_template.get().replace("'",'"'))

            case 'send_my_template':
                troops = {}
                for troop_name, troop_value in self.troops.items():
                    troop_value = troop_value.get()
                    if troop_value:
                        troop_value = int(troop_value)
                        troops[troop_name] = troop_value

        villages = get_villages_id(settings=settings)

        send_info_list = []  # When, from where, attack or help, amount of troops etc.
        for send_from, send_to in zip(sends_from.split(), sends_to.split()):        
            send_info = {}
            send_info['command'] = command_type  # Is it attack or help
            send_info['template_type'] = template_type  # Is it attack or help
            send_info['send_from_village_id'] = villages[send_from][:-1]  # It returns village ID
            send_info['send_to_village_id'] = villages[send_to][:-1]  # It returns village ID
            send_info['url'] = (
                f'https://pl'
                f'{settings["world_number"]}'
                f'.plemiona.pl/game.php?village='
                f'{send_info["send_from_village_id"]}'
                f'&screen=place&target='
                f'{send_info["send_to_village_id"]}'
            )
            send_info['arrival_time'] = arrival_time        
            distance = sqrt(
                pow(int(send_from[:3])-int(send_to[:3]), 2) 
                + pow(int(send_from[4:])-int(send_to[4:]), 2)
                )
            
            troops_speed = {
                'spear': 18,
                'sword': 22,
                'axe': 18,
                'archer': 18,
                'spy': 9,
                'light': 10,
                'marcher': 10,
                'heavy': 11,
                'ram': 30,
                'catapult': 30,
                'knight': 10,
                'snob': 35
            }             

            match template_type:  

                case 'send_all':        
                    send_info['army_type'] = army_type
                    send_info['send_snob'] = send_snob
                    if send_snob == 'send_snob':
                        send_info['snob_amount'] = snob_amount
                        send_info['first_snob_army_size'] = first_snob_army_size

                    troops_dictionary = {
                        'Pikinier': 'spear',
                        'Miecznik': 'sword',
                        'Topornik': 'axe',
                        'Łucznik': 'archer',
                        'Zwiadowca': 'spy',
                        'Lekka kawaleria': 'light',
                        'Łucznik konny': 'marcher',
                        'Ciężka kawaleria': 'heavy',
                        'Taran': 'ram',
                        'Katapulta': 'catapult',
                        'Rycerz': 'knight',
                        'Szlachcic': 'snob'
                    }
                    slowest_troop = self.slowest_troop.get()
                    slowest_troop = troops_dictionary[slowest_troop]
                    send_info['slowest_troop'] = slowest_troop
                    army_speed = troops_speed[slowest_troop]

                case 'send_fake':        
                    send_info['fake_template'] = choosed_fake_template
                    choosed_fake_template = sorted(choosed_fake_template.items(), key=lambda x: x[1]['priority_nubmer'])
                    army_speed = max(troops_speed[troop_name] for troop_name, dict_info in choosed_fake_template if int(dict_info['min_value'])>0)
                
                case 'send_my_template':
                    send_info['troops'] = troops
                    army_speed = max(troops_speed[troop_name] for troop_name in troops.keys())

            travel_time_in_sec = round(army_speed * distance * 60)  # Milisekundy są zaokrąglane do pełnych sekund
            arrival_time_in_sec = time.mktime(time.strptime(arrival_time, '%d.%m.%Y %H:%M:%S:%f'))
            send_info['send_time'] = arrival_time_in_sec - travel_time_in_sec  # sec since epoch

            send_info_list.append(send_info)

        for cell in send_info_list:
            settings['scheduler']['ready_schedule'].append(cell)
        settings['scheduler']['ready_schedule'].sort(key=lambda x: x['send_time'])

        # Scroll-up the page and clear input fields
        self.scroll_able.canvas.yview_moveto(0)
        self.villages_to_use.delete('1.0', tk.END)
        self.villages_destiny.delete('1.0', tk.END)
        MyFunc().custom_error(message='Dodano do planera!', auto_hide=True, parent=self.scroll_able.canvas)

    def create_template(self) -> None:
        """As named it creates fake template to use"""

        def add_to_template() -> None:            

            nonlocal last_row_number, template

            def _forget_row(row_number, troop_name) -> None:
                self.forget_row(frame, row_number)
                del template[troop_name]             

            priority = priority_nubmer.get()
            troop = troop_type.get()
            min = min_value.get()
            max = max_value.get()            

            ttk.Label(frame, text=f'{priority}'                                     
                ).grid(row=last_row_number, column=0)

            ttk.Label(frame, text=f'{troop}'                                     
                ).grid(row=last_row_number, column=1)

            ttk.Label(frame, text=f'{min}'                                     
                ).grid(row=last_row_number, column=2)

            ttk.Label(frame, text=f'{max}'                                     
                ).grid(row=last_row_number, column=3)            

            troop_dictionary = {
                'Pikinier': 'spear',
                'Miecznik': 'sword',
                'Topornik': 'axe',
                'Łucznik': 'archer',
                'Zwiadowca': 'spy',
                'Lekka kawaleria': 'light',
                'Łucznik konny': 'marcher',
                'Ciężka kawaleria': 'heavy',
                'Taran': 'ram',
                'Katapulta': 'catapult',
            }

            troop = troop_dictionary[troop]

            ttk.Button(frame, image=self.minus, 
                bootstyle='primary.Link.TButton',
                command=partial(_forget_row, last_row_number, troop)                          
                ).grid(row=last_row_number, column=4, padx=(0, 10))

            template[troop] = {'priority_nubmer': priority, 'min_value': min, 'max_value': max}

            last_row_number += 1
        
        def redraw_availabe_templates() -> None:
            self.forget_row(self.scroll_able.frame, rows_beetwen=(19, 40))
            self.available_templates()
            self.scroll_able.frame.update_idletasks()
            self.scroll_able.canvas.configure(scrollregion=self.scroll_able.canvas.bbox('all'))

        template = {}
        last_row_number = 4               

        template_window = TopLevel(
            master=self.parent, 
            borderwidth=1, 
            relief='groove'
        )

        frame = template_window.content_frame

        template_name = tk.StringVar()
        priority_nubmer = tk.StringVar()
        troop_type = tk.StringVar()
        min_value = tk.StringVar()
        max_value = tk.StringVar()

        ttk.Label(frame, text='Szablon dobierania jednostek').grid(row=0, column=0, columnspan=5, padx=5, pady=(0, 10))

        ttk.Label(frame, text='Nazwa szablonu').grid(row=1, column=0, columnspan=5, padx=10, pady=10, sticky=tk.W)

        ttk.Entry(frame, textvariable=template_name).grid(row=1, column=0, columnspan=5, padx=10, pady=10, sticky=tk.E)

        ttk.Label(frame, text='Priorytet').grid(row=2, column=0, padx=(10, 5))
        ttk.Label(frame, text='Jednostka').grid(row=2, column=1, padx=5)
        ttk.Label(frame, text='Min').grid(row=2, column=2, padx=5)
        ttk.Label(frame, text='Max').grid(row=2, column=3, padx=(5, 10))

        choose_priority_nubmer = ttk.Combobox(
            frame, 
            textvariable=priority_nubmer, 
            width=3, 
            justify=tk.CENTER
        )
        choose_priority_nubmer.grid(row=3, column=0, padx=(10, 5), pady=(0, 5))
        choose_priority_nubmer['state'] = 'readonly'
        choose_priority_nubmer['values'] = (
            tuple(num for num in range(1, 10))
        )

        choose_troop_type = ttk.Combobox(
            frame, 
            textvariable=troop_type, 
            width=14,
            justify=tk.CENTER
        )
        choose_troop_type.grid(row=3, column=1, padx=5, pady=(0, 5))
        choose_troop_type['state'] = 'readonly'
        choose_troop_type['values'] = (
            'Pikinier', 
            'Miecznik', 
            'Topornik', 
            'Łucznik', 
            'Zwiadowca', 
            'Lekka kawaleria', 
            'Łucznik konny', 
            'Ciężka kawaleria', 
            'Taran', 
            'Katapulta'
        )

        ttk.Entry(frame, textvariable=min_value, width=4, justify=tk.CENTER).grid(row=3, column=2, padx=5, pady=(0, 5))
        ttk.Entry(frame, textvariable=max_value, width=4, justify=tk.CENTER).grid(row=3, column=3, padx=(5, 10), pady=(0, 5))
        ttk.Button(frame, bootstyle='primary.Link.TButton', image=self.plus, command=add_to_template).grid(row=3, column=4, padx=(0, 10), pady=(0, 5))

        def add_to_settings(): settings['scheduler']['fake_templates'][template_name.get()] = template
        ttk.Button(frame, text='Utwórz szablon', command=lambda: [add_to_settings(), template_window.destroy(), redraw_availabe_templates()]).grid(row=50, column=0, columnspan=5, pady=(5, 10))

        MyFunc.center(template_window)
        template_window.attributes('-alpha', 1.0)        

    def forget_row(self, widget_name, row_number: int=0, rows_beetwen: tuple=None) -> None:
        for label in widget_name.grid_slaves():
            if rows_beetwen:
                if rows_beetwen[0] < int(label.grid_info()["row"]) < rows_beetwen[1]:
                    label.grid_forget()                
            elif int(label.grid_info()["row"]) == row_number:
                label.grid_forget()


class TopLevel(tk.Toplevel):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.attributes('-alpha', 0.0)
        self.iconbitmap(default='icons//ikona.ico')        
        self.overrideredirect(True)
        self.attributes('-topmost', 1)

        self.main_frame = ttk.Frame(self, borderwidth=1, relief='groove')
        self.main_frame.grid(row=0, column=0, sticky=('N', 'S', 'E', 'W'))

        self.custom_bar = ttk.Frame(self.main_frame)
        self.custom_bar.grid(row=0, column=0, sticky=('N', 'S', 'E', 'W'))
        self.custom_bar.columnconfigure(3, weight=1)

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky=('N', 'S', 'E', 'W'))

        self.photo = tk.PhotoImage(file='icons//minimize.png')
        self.minimize = self.photo.subsample(2, 2)

        self.minimize_button = ttk.Button(self.custom_bar, bootstyle='primary.Link.TButton', image=self.minimize, command=self._hide)
        self.minimize_button.grid(row=0, column=4, padx=(5, 0), pady=5, sticky='E')

        self.photo = tk.PhotoImage(file='icons//exit.png')
        self.exit = self.photo.subsample(8, 8)

        self.exit_button = ttk.Button(self.custom_bar, bootstyle='primary.Link.TButton', image=self.exit, command=self.destroy)
        self.exit_button.grid(row=0, column=5, padx=(0, 5), pady=3, sticky='E')      

        self.custom_bar.bind('<Button-1>', lambda event: self._get_pos(event, 'custom_bar'))

    def _hide(self):
        self.attributes('-alpha', 0.0)
        self.overrideredirect(False)
        self.iconify()
        def show(event=None):
            self.overrideredirect(True)
            self.attributes('-alpha', 1.0)
        self.minimize_button.bind("<Map>", show)

    def _get_pos(self, event, *args) -> None:
        xwin = self.winfo_x()
        ywin = self.winfo_y()
        startx = event.x_root
        starty = event.y_root

        ywin = ywin - starty
        xwin = xwin - startx

        def move_window(event):
            self.geometry(f'+{event.x_root + xwin}+{event.y_root + ywin}')
        startx = event.x_root
        starty = event.y_root

        for arg in args:
            getattr(self, arg).bind('<B1-Motion>', move_window)   


class MainWindow:
    
    entries_content = {}
    elements_state = []

    def __init__(self) -> None:
        self.master = tk.Tk()
        self.master.attributes('-alpha', 0.0)
        self.master.iconbitmap(default='icons//ikona.ico')        
        self.master.title('Tribal Wars 24/7')        
        self.master.overrideredirect(True)
        self.master.attributes('-topmost', 1)

        # main_frame -> custom_bar, content_frame
        self.main_frame = ttk.Frame(self.master, borderwidth=1, relief='groove')
        self.main_frame.grid(row=0, column=0, sticky=('N', 'S', 'E', 'W'))

        self.custom_bar = ttk.Frame(self.main_frame)
        self.custom_bar.grid(row=0, column=0, sticky=('N', 'S', 'E', 'W'))
        self.custom_bar.columnconfigure(3, weight=1)

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky=('N', 'S', 'E', 'W'))

        # custom_bar
        self.title_label = ttk.Label(self.custom_bar, text='Tribal Wars Bot')
        self.title_label.grid(row=0, column=1, padx=(5, 0) , sticky='W')

        self.time = tk.StringVar()
        self.title_timer = ttk.Label(self.custom_bar, textvariable=self.time)
        self.title_timer.grid(row=0, column=2, padx=5)

        self.entries_content['world_in_title'] = tk.StringVar(value=' ')
        self.title_world = ttk.Label(self.custom_bar, textvariable=self.entries_content['world_in_title'])
        self.title_world.grid(row=0, column=3, padx=(5, 0), sticky='E')

        self.photo = tk.PhotoImage(file='icons//minimize.png')
        self.minimize = self.photo.subsample(2, 2)

        self.minimize_button = ttk.Button(self.custom_bar, bootstyle='primary.Link.TButton', image=self.minimize, command=self.hide)
        self.minimize_button.grid(row=0, column=4, padx=(5, 0), pady=5, sticky='E')

        self.photo = tk.PhotoImage(file='icons//exit.png')
        self.exit = self.photo.subsample(8, 8)

        self.exit_button = ttk.Button(self.custom_bar, bootstyle='primary.Link.TButton', image=self.exit, 
                                command= lambda: [MyFunc.save_entry_to_settings(self.entries_content),
                                subprocess.run('taskkill /IM chromedriver.exe /F') if driver else None, self.master.destroy()])
        self.exit_button.grid(row=0, column=5, padx=(0, 5), pady=3, sticky='E')      

        self.custom_bar.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'custom_bar'))
        self.title_label.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'title_label'))
        self.title_world.bind('<Button-1>', lambda event: self.show_world_chooser_window(event))
        self.title_timer.bind('<Button-1>', lambda event: self.show_jobs_to_do_window(event))

        # content_frame

        # Notebook with frames 
        n = ttk.Notebook(self.content_frame)
        n.grid(row=1, column=0, padx=5, pady=(0, 5), sticky=('N', 'S', 'E', 'W'))
        f1 = ttk.Frame(n)
        f2 = ttk.Frame(n)
        f3 = ttk.Frame(n)
        f4 = ttk.Frame(n)
        f5 = ttk.Frame(n)
        n.add(f1, text='Farma')
        n.add(f2, text='Zbieractwo')
        n.add(f3, text='Planer')
        n.add(f4, text='Rynek')
        n.add(f5, text='Ustawienia')        
        self.content_frame.rowconfigure(0, weight=1)
        self.content_frame.columnconfigure(0, weight=1)

        # f1 -> 'Farma'
        templates = ttk.Notebook(f1)
        templates.grid(pady=5, padx=5, sticky=('N', 'S', 'E', 'W'))
        A = ttk.Frame(templates)
        B = ttk.Frame(templates)
        C = ttk.Frame(templates)
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

        self.entries_content['A']['active'] = tk.StringVar()
        self.active_A = ttk.Checkbutton(A, text='Aktywuj szablon', 
                                    variable=self.entries_content['A']['active'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: MyFunc.change_state(*self.elements_state[0]))
        self.active_A.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
        self.elements_state.append([A, 'active', self.entries_content['A'], True, self.active_A])
        
        ttk.Separator(A, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky=('W', 'E'))

        self.wall = ttk.Label(A, text='Poziom muru')
        self.wall.grid(row=2, column=0, columnspan=2, pady=(20, 15), padx=5, sticky='W')

        self.entries_content['A']['wall_ignore'] = tk.StringVar()
        self.wall_ignore = ttk.Checkbutton(A, text='Ignoruj poziom', 
                                       variable=self.entries_content['A']['wall_ignore'], 
                                       onvalue=True, offvalue=False,
                                       command=lambda: MyFunc.change_state(*self.elements_state[1]))
        self.wall_ignore.grid(row=3, column=0, pady=5, padx=(25, 5), sticky='W')     

        self.min_wall_level = ttk.Label(A, text='Min')
        self.min_wall_level.grid(row=4, column=0, pady=5, padx=(25, 5), sticky='W')

        self.entries_content['A']['min_wall'] = tk.StringVar()
        self.min_wall_level_input = ttk.Entry(A, width=5, textvariable=self.entries_content['A']['min_wall'], justify='center')
        self.min_wall_level_input.grid(row=4, column=1, pady=5, padx=(5, 25), sticky='E')

        self.max_wall_level = ttk.Label(A, text='Max')
        self.max_wall_level.grid(row=5, column=0, pady=5, padx=(25, 5), sticky='W')

        self.entries_content['A']['max_wall'] = tk.StringVar()
        self.max_wall_level_input_A = ttk.Entry(A, width=5, textvariable=self.entries_content['A']['max_wall'], justify='center')
        self.max_wall_level_input_A.grid(row=5, column=1, pady=5, padx=(5, 25), sticky='E')
        self.elements_state.append([[self.min_wall_level_input, self.max_wall_level_input_A], 'wall_ignore', self.entries_content['A']])               

        self.attacks = ttk.Label(A, text='Wysyłka ataków')
        self.attacks.grid(row=6, column=0, columnspan=2, pady=(20, 10), padx=5, sticky='W')        

        self.entries_content['A']['max_attacks'] = tk.StringVar()
        self.max_attacks_A = ttk.Checkbutton(A, text='Maksymalna ilość', 
                                    variable=self.entries_content['A']['max_attacks'], 
                                    onvalue=True, offvalue=False, 
                                    command=lambda: MyFunc.change_state(*self.elements_state[2]))
        self.max_attacks_A.grid(row=7, column=0, pady=5, padx=(25, 5), sticky='W')

        self.attacks = ttk.Label(A, text='Ilość ataków')
        self.attacks.grid(row=8, column=0, pady=(5, 10), padx=(25, 5), sticky='W')

        self.entries_content['A']['attacks_number'] = tk.StringVar()
        self.attacks_number_input_A = ttk.Entry(A, width=5, textvariable=self.entries_content['A']['attacks_number'], justify='center')
        self.attacks_number_input_A.grid(row=8, column=1, pady=(5, 10), padx=(5, 25), sticky='E')
        self.elements_state.append([self.attacks_number_input_A, 'max_attacks', self.entries_content['A']])
        #endregion
        
        # Szablon B
        #region
        B.columnconfigure(0, weight=1)
        B.columnconfigure(1, weight=1)
        self.entries_content['B'] = {}
        
        self.entries_content['B']['active'] = tk.StringVar()
        self.active_B = ttk.Checkbutton(B, text='Aktywuj szablon', 
                                    variable=self.entries_content['B']['active'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: MyFunc.change_state(*self.elements_state[3]))
        self.active_B.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
        self.elements_state.append([B, 'active', self.entries_content['B'], True, self.active_B])

        ttk.Separator(B, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky=('W', 'E'))

        self.wall = ttk.Label(B, text='Poziom muru')
        self.wall.grid(row=2, column=0, columnspan=2, pady=(20, 15), padx=5, sticky='W')

        self.entries_content['B']['wall_ignore'] = tk.StringVar()
        self.wall_ignore_B = ttk.Checkbutton(B, text='Ignoruj poziom', 
                                       variable=self.entries_content['B']['wall_ignore'], 
                                       onvalue=True, offvalue=False,
                                       command=lambda: MyFunc.change_state(*self.elements_state[4]))
        self.wall_ignore_B.grid(row=3, column=0, pady=5, padx=(25, 5), sticky='W')          

        self.min_wall_level = ttk.Label(B, text='Min')
        self.min_wall_level.grid(row=4, column=0, pady=5, padx=(25, 5), sticky='W')

        self.entries_content['B']['min_wall'] = tk.StringVar()
        self.min_wall_level_input_B = ttk.Entry(B, width=5, textvariable=self.entries_content['B']['min_wall'], justify='center')
        self.min_wall_level_input_B.grid(row=4, column=1, pady=5, padx=(5, 25), sticky='E')

        self.max_wall_level = ttk.Label(B, text='Max')
        self.max_wall_level.grid(row=5, column=0, pady=5, padx=(25, 5), sticky='W')

        self.entries_content['B']['max_wall'] = tk.StringVar()
        self.max_wall_level_input_B = ttk.Entry(B, width=5, textvariable=self.entries_content['B']['max_wall'], justify='center')
        self.max_wall_level_input_B.grid(row=5, column=1, pady=5, padx=(5, 25), sticky='E')
        self.elements_state.append([[self.min_wall_level_input_B, self.max_wall_level_input_B], 'wall_ignore', self.entries_content['B']])               

        self.attacks = ttk.Label(B, text='Wysyłka ataków')
        self.attacks.grid(row=6, column=0, columnspan=2, pady=(20, 10), padx=5, sticky='W')        

        self.entries_content['B']['max_attacks'] = tk.StringVar()
        self.max_attacks_B = ttk.Checkbutton(B, text='Maksymalna ilość', 
                                    variable=self.entries_content['B']['max_attacks'], 
                                    onvalue=True, offvalue=False, 
                                    command=lambda: MyFunc.change_state(*self.elements_state[5]))
        self.max_attacks_B.grid(row=7, column=0, pady=5, padx=(25, 5), sticky='W')

        self.attacks = ttk.Label(B, text='Ilość ataków')
        self.attacks.grid(row=8, column=0, pady=(5, 10), padx=(25, 5), sticky='W')

        self.entries_content['B']['attacks_number'] = tk.StringVar()
        self.attacks_number_input_B = ttk.Entry(B, width=5, textvariable=self.entries_content['B']['attacks_number'], justify='center')
        self.attacks_number_input_B.grid(row=8, column=1, pady=(5, 10), padx=(5, 25), sticky='E')
        self.elements_state.append([self.attacks_number_input_B, 'max_attacks', self.entries_content['B']])
        #endregion        
        
        # Szablon C
        #region
        C.columnconfigure(1, weight=1)
        C.columnconfigure(0, weight=1)
        self.entries_content['C'] = {}

        self.entries_content['C']['active'] = tk.StringVar()
        self.active_C = ttk.Checkbutton(C, text='Aktywuj szablon', 
                                    variable=self.entries_content['C']['active'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: MyFunc.change_state(*self.elements_state[6]))
        self.active_C.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
        self.elements_state.append([C, 'active', self.entries_content['C'], True, self.active_C])

        ttk.Separator(C, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky=('W', 'E'))

        self.wall = ttk.Label(C, text='Poziom muru')
        self.wall.grid(row=2, column=0, columnspan=2, pady=(20, 15), padx=5, sticky='W')

        self.entries_content['C']['wall_ignore'] = tk.StringVar()
        self.wall_ignore_C = ttk.Checkbutton(C, text='Ignoruj poziom', 
                                       variable=self.entries_content['C']['wall_ignore'], 
                                       onvalue=True, offvalue=False,
                                       command=lambda: MyFunc.change_state(*self.elements_state[7]))
        self.wall_ignore_C.grid(row=3, column=0, pady=5, padx=(25, 5), sticky='W')  

        self.min_wall_level = ttk.Label(C, text='Min')
        self.min_wall_level.grid(row=4, column=0, pady=5, padx=(25, 5), sticky='W')

        self.entries_content['C']['min_wall'] = tk.StringVar()
        self.min_wall_level_input_C = ttk.Entry(C, width=5, textvariable=self.entries_content['C']['min_wall'], justify='center')
        self.min_wall_level_input_C.grid(row=4, column=1, pady=5, padx=(5, 25), sticky='E')

        self.max_wall_level = ttk.Label(C, text='Max')
        self.max_wall_level.grid(row=5, column=0, pady=5, padx=(25, 5), sticky='W')

        self.entries_content['C']['max_wall'] = tk.StringVar()
        self.max_wall_level_input_C = ttk.Entry(C, width=5, textvariable=self.entries_content['C']['max_wall'], justify='center')
        self.max_wall_level_input_C.grid(row=5, column=1, pady=5, padx=(5, 25), sticky='E')
        self.elements_state.append([[self.min_wall_level_input_C, self.max_wall_level_input_C], 'wall_ignore', self.entries_content['C']])               

        self.attacks = ttk.Label(C, text='Wysyłka ataków')
        self.attacks.grid(row=6, column=0, pady=(20, 10), padx=5, sticky='W')        

        self.entries_content['C']['max_attacks'] = tk.StringVar()
        self.max_attacks_C = ttk.Checkbutton(C, text='Maksymalna ilość', 
                                    variable=self.entries_content['C']['max_attacks'], 
                                    onvalue=True, offvalue=False, 
                                    command=lambda: MyFunc.change_state(*self.elements_state[8]))
        self.max_attacks_C.grid(row=7, column=0, pady=5, padx=(25, 5), sticky='W')

        self.attacks = ttk.Label(C, text='Ilość ataków')
        self.attacks.grid(row=8, column=0, pady=(5, 10), padx=(25, 5), sticky='W')

        self.entries_content['C']['attacks_number'] = tk.StringVar()
        self.attacks_number_input_C = ttk.Entry(C, width=5, textvariable=self.entries_content['C']['attacks_number'], justify='center')
        self.attacks_number_input_C.grid(row=8, column=1, pady=(5, 10), padx=(5, 25), sticky='E')
        self.elements_state.append([self.attacks_number_input_C, 'max_attacks', self.entries_content['C']])
        #endregion

        # f2 -> 'Zbieractwo'
        #region
        f2.columnconfigure(0, weight=1)
        
        self.entries_content['gathering'] = {}
        self.entries_content['gathering_troops'] = {'spear': {'left_in_village': tk.StringVar()},
                                                    'sword': {'left_in_village': tk.StringVar()}, 
                                                    'axe': {'left_in_village': tk.StringVar()}, 
                                                    'archer': {'left_in_village': tk.StringVar()}, 
                                                    'light': {'left_in_village': tk.StringVar()}, 
                                                    'marcher': {'left_in_village': tk.StringVar()}, 
                                                    'heavy': {'left_in_village': tk.StringVar()}, 
                                                    'knight': {'left_in_village': tk.StringVar()}}

        self.entries_content['gathering']['active'] = tk.StringVar()
        self.active_gathering = ttk.Checkbutton(f2, text='Aktywuj zbieractwo', 
                                    variable=self.entries_content['gathering']['active'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: MyFunc.change_state(*self.elements_state[9]))
        self.active_gathering.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
        self.elements_state.append([f2, 'active', self.entries_content['gathering'], True, self.active_gathering])
        
        ttk.Separator(f2, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky=('W', 'E'))

        ttk.Label(f2, text='Ustawienia').grid(row=5, columnspan=2, padx=5, pady=(20, 15), sticky='W')     

        ttk.Label(f2 , text='Grupa zbieractwa').grid(row=6, column=0, padx=(25, 5), pady=5, sticky='W')        

        ttk.Combobox(f2)

        self.entries_content['gathering_group'] = tk.StringVar()
        if 'groups' not in settings:
            settings['groups'] = None
        self.gathering_group = ttk.Combobox(f2, textvariable=self.entries_content['gathering_group'], justify='center', width=16)
        self.gathering_group.grid(row=6, column=1, padx=(5, 25), pady=5, sticky='E')
        self.gathering_group.set('Wybierz grupę')
        self.gathering_group['values'] = settings['groups']

        self.gathering_max_resources = ttk.Label(f2, text='Maks surowców do zebrania')
        self.gathering_max_resources.grid(row=7, column=0, padx=(25, 5), pady=(10, 5), sticky='W')

        self.entries_content['gathering_max_resources'] = tk.StringVar()
        self.gathering_max_resources_input = ttk.Entry(f2, textvariable=self.entries_content['gathering_max_resources'], justify='center', width=18)
        self.gathering_max_resources_input.grid(row=7, column=1, padx=(5, 25), pady=(10, 5), sticky='E')

        ttk.Label(f2, text='Dozwolone jednostki do wysłania').grid(row=8, columnspan=2, padx=5, pady=(20, 15), sticky='W')

        self.entries_content['gathering_troops']['spear']['use'] = tk.StringVar()
        self.spear_photo = tk.PhotoImage(file='icons//spear.png')
        self.gathering_spear = ttk.Checkbutton(f2, text='Pikinier', image=self.spear_photo, compound='left', 
                                    variable=self.entries_content['gathering_troops']['spear']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_spear.grid(row=9, column=0, padx=(25, 5), pady=5, sticky='W')

        self.entries_content['gathering_troops']['light']['use'] = tk.StringVar()
        self.light_photo = tk.PhotoImage(file='icons//light.png')
        self.gathering_light = ttk.Checkbutton(f2, text='Lekka kawaleria', image=self.light_photo, compound='left', 
                                    variable=self.entries_content['gathering_troops']['light']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_light.grid(row=9, column=1, padx=(5, 25), pady=5, sticky='W')

        self.entries_content['gathering_troops']['sword']['use'] = tk.StringVar()
        self.sword_photo = tk.PhotoImage(file='icons//sword.png')
        self.gathering_sword = ttk.Checkbutton(f2, text='Miecznik', image=self.sword_photo, compound='left', 
                                    variable=self.entries_content['gathering_troops']['sword']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_sword.grid(row=10, column=0, padx=(25, 5), pady=5, sticky='W')

        self.entries_content['gathering_troops']['marcher']['use'] = tk.StringVar()
        self.marcher_photo = tk.PhotoImage(file='icons//marcher.png')
        self.gathering_marcher = ttk.Checkbutton(f2, text='Łucznik konny', image=self.marcher_photo, compound='left', 
                                    variable=self.entries_content['gathering_troops']['marcher']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_marcher.grid(row=10, column=1, padx=(5, 25), pady=5, sticky='W')

        self.entries_content['gathering_troops']['axe']['use'] = tk.StringVar()
        self.axe_photo = tk.PhotoImage(file='icons//axe.png')
        self.gathering_axe = ttk.Checkbutton(f2, text='Topornik', image=self.axe_photo, compound='left', 
                                    variable=self.entries_content['gathering_troops']['axe']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_axe.grid(row=11, column=0, padx=(25, 5), pady=5, sticky='W')

        self.entries_content['gathering_troops']['heavy']['use'] = tk.StringVar()
        self.heavy_photo = tk.PhotoImage(file='icons//heavy.png')
        self.gathering_heavy = ttk.Checkbutton(f2, text='Ciężki kawalerzysta', image=self.heavy_photo, compound='left', 
                                    variable=self.entries_content['gathering_troops']['heavy']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_heavy.grid(row=11, column=1, padx=(5, 25), pady=5, sticky='W')

        self.entries_content['gathering_troops']['archer']['use'] = tk.StringVar()
        self.archer_photo = tk.PhotoImage(file='icons//archer.png')
        self.gathering_archer = ttk.Checkbutton(f2, text='Łucznik', image=self.archer_photo, compound='left', 
                                    variable=self.entries_content['gathering_troops']['archer']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_archer.grid(row=12, column=0, padx=(25, 5), pady=(5, 10), sticky='W')

        self.entries_content['gathering_troops']['knight']['use'] = tk.StringVar()
        self.knight_photo = tk.PhotoImage(file='icons//knight.png')
        self.gathering_knight = ttk.Checkbutton(f2, text='Rycerz', image=self.knight_photo, compound='left', 
                                    variable=self.entries_content['gathering_troops']['knight']['use'], 
                                    onvalue=True, offvalue=False)
        self.gathering_knight.grid(row=12, column=1, padx=(5, 25), pady=(5, 10), sticky='W')

        ttk.Label(f2, text='Poziomy zbieractwa do pominięcia').grid(row=13, columnspan=2, padx=5, pady=(20, 15), sticky='W')

        f2_1 = ttk.Frame(f2)
        f2_1.grid(row=14, column=0, columnspan=2)

        self.entries_content['gathering']['ommit'] = {}

        self.entries_content['gathering']['ommit']['first_level_gathering'] = tk.StringVar()
        self.ommit_first_level_gathering = ttk.Checkbutton(f2_1, text='Pierwszy', 
                                    variable=self.entries_content['gathering']['ommit']['first_level_gathering'], 
                                    onvalue=True, offvalue=False)
        self.ommit_first_level_gathering.grid(row=14, column=0, padx=(25, 5), pady=(5, 10))

        self.entries_content['gathering']['ommit']['second_level_gathering'] = tk.StringVar()
        self.ommit_second_level_gathering = ttk.Checkbutton(f2_1, text='Drugi', 
                                    variable=self.entries_content['gathering']['ommit']['second_level_gathering'], 
                                    onvalue=True, offvalue=False)
        self.ommit_second_level_gathering.grid(row=14, column=1, padx=10, pady=(5, 10))

        self.entries_content['gathering']['ommit']['thrid_level_gathering'] = tk.StringVar()
        self.ommit_thrid_level_gathering = ttk.Checkbutton(f2_1, text='Trzeci', 
                                    variable=self.entries_content['gathering']['ommit']['thrid_level_gathering'], 
                                    onvalue=True, offvalue=False)
        self.ommit_thrid_level_gathering.grid(row=14, column=2, padx=10, pady=(5, 10))

        self.entries_content['gathering']['ommit']['fourth_level_gathering'] = tk.StringVar()
        self.ommit_fourth_level_gathering = ttk.Checkbutton(f2_1, text='Czwarty', 
                                    variable=self.entries_content['gathering']['ommit']['fourth_level_gathering'], 
                                    onvalue=True, offvalue=False)
        self.ommit_fourth_level_gathering.grid(row=14, column=3, padx=(5, 25), pady=(5, 10))

        self.entries_content['gathering']['stop_if_incoming_attacks'] = tk.StringVar()
        self.stop_if_incoming_attacks = ttk.Checkbutton(f2, text='Wstrzymaj wysyłkę wojsk gdy wykryto nadchodzące ataki', 
                                    variable=self.entries_content['gathering']['stop_if_incoming_attacks'], 
                                    onvalue=True, offvalue=False)
        self.stop_if_incoming_attacks.grid(row=15, column=0, columnspan=2, padx=25, pady=(10, 5))

        #endregion

        # f3 -> 'Planer'

        NotebookSchedul(parent=f3, entries_content=self.entries_content)       

        # f4 -> 'Rynek'
        #region
        f4.columnconfigure(0, weight=1)
        
        self.entries_content['market'] = {'wood': {}, 'stone': {}, 'iron': {}}

        self.entries_content['premium_exchange'] = tk.StringVar()
        self.active_premium_exchange = ttk.Checkbutton(f4, text='Aktywuj giełde premium', 
                                    variable=self.entries_content['premium_exchange'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: MyFunc.change_state(*self.elements_state[10]))
        self.active_premium_exchange.grid(row=0, column=0, columnspan=2, padx=5, pady=20)
        self.elements_state.append([f4, 'premium_exchange', self.entries_content, True, self.active_premium_exchange])
        
        ttk.Separator(f4, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky=('W', 'E'))

        # Label(f4, text='Ustawienia').grid(row=2, columnspan=2, padx=5, pady=(20, 15), sticky='W')  

        ttk.Label(f4 , text='Maksymalny kurs sprzedaży').grid(row=3, column=0, padx=5, pady=(20, 15), sticky='W')

        self.wood_photo = tk.PhotoImage(file='icons//wood.png')
        ttk.Label(f4, text='Drewno', image=self.wood_photo, compound='left').grid(row=4, column=0, padx=(25, 5), pady=5, sticky='W')
        self.entries_content['market']['wood']['max_exchange_rate'] = tk.StringVar()
        self.max_wood_exchange_rate = ttk.Entry(f4, textvariable=self.entries_content['market']['wood']['max_exchange_rate'], justify='center', width=6)
        self.max_wood_exchange_rate.grid(row=4, column=1, padx=(5, 25), pady=(10, 5), sticky='E')        

        self.stone_photo = tk.PhotoImage(file='icons//stone.png')
        ttk.Label(f4, text='Cegła', image=self.stone_photo, compound='left').grid(row=5, column=0, padx=(25, 5), pady=5, sticky='W')
        self.entries_content['market']['stone']['max_exchange_rate'] = tk.StringVar()
        self.max_stone_exchange_rate = ttk.Entry(f4, textvariable=self.entries_content['market']['stone']['max_exchange_rate'], justify='center', width=6)
        self.max_stone_exchange_rate.grid(row=5, column=1, padx=(5, 25), pady=(10, 5), sticky='E')  

        self.iron_photo = tk.PhotoImage(file='icons//iron.png')
        ttk.Label(f4, text='Żelazo', image=self.iron_photo, compound='left').grid(row=6, column=0, padx=(25, 5), pady=5, sticky='W')
        self.entries_content['market']['iron']['max_exchange_rate'] = tk.StringVar()
        self.max_iron_exchange_rate = ttk.Entry(f4, textvariable=self.entries_content['market']['iron']['max_exchange_rate'], justify='center', width=6)
        self.max_iron_exchange_rate.grid(row=6, column=1, padx=(5, 25), pady=(10, 5), sticky='E')

        def show_label_and_text_widget() -> None:
            
            def clear_text_widget(event) -> None:
                if self.villages_to_ommit_text.get('1.0', '1.5') == 'Wklej':
                    self.villages_to_ommit_text.delete('1.0', 'end')
                    self.villages_to_ommit_text.unbind('<Button-1>')

            def add_villages_list() -> None:
                if self.villages_to_ommit_text.compare("end-1c", "==", "1.0"):
                    self.villages_to_ommit_text.insert(
                        '1.0', 
                        'Wklej wioski w formacie XXX|YYY które chcesz aby były pomijane. ' 
                        'Wioski powinny być oddzielone spacją, tabulatorem lub enterem.')
                    return
                if self.villages_to_ommit_text.get('1.0', '1.5') == 'Wklej':
                    self.entries_content['market_exclude_villages'].set('')
                else:
                    self.entries_content['market_exclude_villages'].set(self.villages_to_ommit_text.get('1.0', 'end'))
                    settings['market_exclude_villages'] = self.villages_to_ommit_text.get('1.0', 'end')
                self.villages_to_ommit_text.grid_forget()
                self.confirm_button.grid_forget()

                self.success_label = ttk.Label(f4, text='Dodano!')
                self.success_label.grid(row=8, column=0, columnspan=2, padx=5, pady=15)
                self.master.update_idletasks()
                time.sleep(1)
                self.success_label.grid_forget()
                del self.villages_to_ommit_text


            if hasattr(self, 'villages_to_ommit_text'):
                print(self.villages_to_ommit_text)
                self.villages_to_ommit_text.grid_forget()
                self.confirm_button.grid_forget()
                del self.villages_to_ommit_text
                return

            self.villages_to_ommit_text = tk.Text(f4, height=6, width=50, wrap='word')
            self.villages_to_ommit_text.grid(row=8, column=0, columnspan=2, padx=5, pady=10)
            if settings['market_exclude_villages'] and settings['market_exclude_villages'] != '0':
                self.villages_to_ommit_text.insert('1.0', settings['market_exclude_villages'])
            else:
                self.villages_to_ommit_text.insert('1.0', 'Wklej wioski w formacie XXX|YYY które chcesz aby były pomijane. Wioski powinny być oddzielone spacją, tabulatorem lub enterem.')

            self.confirm_button = ttk.Button(f4, text='Dodaj', command=add_villages_list)
            self.confirm_button.grid(row=9, column=0, columnspan=2, padx=5, pady=5)

            self.villages_to_ommit_text.bind('<Button-1>', clear_text_widget)

        self.entries_content['market_exclude_villages'] = tk.StringVar()
        self.add_village_exceptions_button = ttk.Button(f4, text='Dodaj wykluczenia', command=show_label_and_text_widget)
        self.add_village_exceptions_button.grid(row=7, column=0, columnspan=2, padx=5, pady=(30,5))    
        

        #endregion

        # f5 -> 'Ustawienia'
        f5.columnconfigure(0, weight=1)
        f5.columnconfigure(1, weight=1)

        self.world_number = ttk.Label(f5, text='Numer świata')
        self.world_number.grid(row=0, column=0, padx=5, pady=(10, 5), sticky='E')

        self.entries_content['world_number'] = tk.StringVar()
        self.world_number_trace = self.entries_content['world_number'].trace_add('write', self.world_number_change)
        self.world_number_input = ttk.Entry(f5, textvariable=self.entries_content['world_number'], width=3, justify='center')
        self.world_number_input.grid(row=0, column=1, padx=5, pady=(10, 5), sticky='W')

        self.entries_content['farm_group'] = tk.StringVar()
        self.farm_group = ttk.Combobox(f5, textvariable=self.entries_content['farm_group'])
        self.farm_group.grid(row=3, column=0, padx=5, pady=5, sticky='E')
        self.farm_group.set('Wybierz grupę')
        self.farm_group['values'] = settings['groups']

        self.update_groups = ttk.Button(f5, text='update', command=lambda: threading.Thread(target=self.check_groups, name='checking_groups', daemon=True).start())
        self.update_groups.grid(row=3, column=1, padx=5, pady=5, sticky='W')

        self.farm_sleep_time_label = ttk.Label(f5, text='Czas przed kolejnym wysłaniem farmy [min]')
        self.farm_sleep_time_label.grid(row=4, column=0, padx=5, pady=5, sticky='E')

        self.entries_content['farm_sleep_time'] = tk.StringVar()
        self.farm_sleep_time = ttk.Entry(f5, textvariable=self.entries_content['farm_sleep_time'], width=5, justify='center')
        self.farm_sleep_time.grid(row=4, column=1, padx=5, pady=5, sticky='W')

        self.entries_content['account_premium'] = tk.StringVar()
        self.account_premium = ttk.Checkbutton(f5, text='Konto premium', 
                                    variable=self.entries_content['account_premium'], 
                                    onvalue=True, offvalue=False)
        self.account_premium.grid(row=6, column=0, columnspan=2, padx=5, pady=20)

        self.entries_content['check_incoming_attacks'] = tk.StringVar()
        self.check_incoming_attacks = ttk.Checkbutton(f5, text='Etykiety nadchodzących ataków', 
                                    variable=self.entries_content['check_incoming_attacks'], 
                                    onvalue=True, offvalue=False)
        self.check_incoming_attacks.grid(row=7, column=0, columnspan=2, padx=5, pady=10)

        self.check_incoming_attacks_label = ttk.Label(f5, text='Twórz etykiety ataków co [min]')
        self.check_incoming_attacks_label.grid(row=8, column=0, padx=5, pady=5, sticky='E')

        self.entries_content['check_incoming_attacks_sleep_time'] = tk.StringVar()
        self.check_incoming_attacks_sleep_time = ttk.Entry(f5, textvariable=self.entries_content['check_incoming_attacks_sleep_time'], width=5, justify='center')
        self.check_incoming_attacks_sleep_time.grid(row=8, column=1, padx=5, pady=5, sticky='W')

        self.entries_content['email_notifications'] = tk.StringVar()
        self.email_notifications = ttk.Checkbutton(f5, text='Powiadomienia email o idących grubasach', 
                                    variable=self.entries_content['email_notifications'], 
                                    onvalue=True, offvalue=False)
        self.email_notifications.grid(row=9, column=0, columnspan=2, padx=5, pady=10)


        # content_frame
        self.save_button = ttk.Button(self.content_frame, text='zapisz', command=lambda: MyFunc.save_entry_to_settings(self.entries_content))
        self.save_button.grid(row=2, column=0, padx=5, pady=5, sticky=('W', 'E'))

        self.run_button = ttk.Button(self.content_frame, text='uruchom', command=lambda: threading.Thread(target=self.run, name='main_function', daemon=True).start())
        self.run_button.grid(row=3, column=0, padx=5, pady=5, sticky=('W', 'E'))

        # Other things
        MyFunc.fill_entry_from_settings(self.entries_content)
        MyFunc.save_entry_to_settings(self.entries_content)

        for list in self.elements_state:
            MyFunc.change_state_on_settings_load(*list)        

        self.master.withdraw()          

    def add_new_world_settings(self):
        global settings
        
        world_number = self.entries_content['world_number'].get()

        if not os.path.isdir('settings'):
            os.mkdir('settings')

        settings_list = os.listdir('settings')

        # if any(world_number in settings_name for settings_name in settings_list):
        #     print('it exist')
        # print(world_number)
        # print(settings_list)
        # input()

        if any(world_number in settings_name for settings_name in settings_list):  # os.path.exists(f'settings/{world_number}.json'):
            MyFunc().custom_error('Ustawienia tego świata już istnieją!')
        elif len(settings_list) == 0:
            self.entries_content['world_in_title'].set(f'PL{world_number}')
        else:            
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
            self.entries_content['world_number'].set(value=world_number)
            MyFunc.save_entry_to_settings(self.entries_content)
            self.entries_content['world_in_title'].set(f'PL{world_number}')
    
    def check_groups(self):

        self.farm_group.set('updating...')
        self.gathering_group.set('updating...')
        MyFunc.save_entry_to_settings(self.entries_content)
        bot_functions.check_groups(driver, settings, MyFunc.run_driver, *[self.farm_group, self.gathering_group])

    def hide(self):
        self.master.attributes('-alpha', 0.0)
        self.master.overrideredirect(False)
        self.master.iconify()
        def show(event=None):
            self.master.overrideredirect(True)
            self.master.attributes('-alpha', 1.0)
        self.minimize_button.bind("<Map>", show)    

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

            # Usuwa z listy nieaktualne terminy wysyłki wojsk (których termin już upłynął)
            if _settings['scheduler']['ready_schedule']:
                current_time = time.time()
                _settings['scheduler']['ready_schedule'] = [
                    value for value in _settings['scheduler']['ready_schedule'] 
                    if value['send_time'] > current_time
                    ]
                # Dodaj planer do listy to_do
                for send_info in _settings['scheduler']['ready_schedule']:                
                    self.to_do.append({'func': 'send_troops', 'start_time': send_info['send_time']-8, 'world_number': _settings['world_number']})
        
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

                            case 'send_troops':
                                send_number_times = bot_functions.send_troops(driver, _settings)

                                # Clean from _settings and self.to_do
                                del _settings['scheduler']['ready_schedule'][0:send_number_times]

                                if send_number_times > 1:
                                    index_to_del = []
                                    for index, row_data in enumerate(self.to_do):
                                        if row_data['func'] == 'send_troops':
                                            index_to_del.append(index)
                                            if len(index_to_del) == send_number_times:
                                                break
                                    for index in sorted(index_to_del, reverse=True)[:-1]:
                                        del self.to_do[index]        

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

    def show_world_chooser_window(self, event) -> None:
        """Show new window with available worlds settings to choose"""

        def change_world(world_number: str) -> None:
            global settings

            self.entries_content['world_number'].trace_remove('write', self.world_number_trace)

            if os.path.exists(f'settings/{world_number}.json'):
                # Save current settings before changing to other
                MyFunc.save_entry_to_settings(self.entries_content)
                settings = MyFunc.load_settings(f'settings/{world_number}.json')
                # Usuwa z listy nieaktualne terminy wysyłki wojsk (których termin już upłynął)
                if settings['scheduler']['ready_schedule']:
                    current_time = time.time()
                    settings['scheduler']['ready_schedule'] = [
                        value for value in settings['scheduler']['ready_schedule'] 
                        if value['send_time'] > current_time
                        ]
                MyFunc.fill_entry_from_settings(self.entries_content)
                for list in self.elements_state:
                    MyFunc.change_state_on_settings_load(*list)
                self.entries_content['world_in_title'].set(f'PL{world_number}')
                self.world_chooser_window.destroy()

            self.world_number_trace = self.entries_content['world_number'].trace_add('write', self.world_number_change)

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

        self.world_chooser_window = tk.Toplevel(self.title_world, borderwidth=1, relief='groove')
        self.world_chooser_window.attributes('-alpha', 0.0)
        self.world_chooser_window.overrideredirect(True)
        self.world_chooser_window.attributes('-topmost', 1) 
        
        # for color_label in style.colors.label_iter():
        #     print(style.colors.get(color_label))

        for index, settings_file_name in enumerate(os.listdir('settings')):
            world_number = settings_file_name[:settings_file_name.find('.')]
            ttk.Button(self.world_chooser_window, bootstyle='secondary-outline', text=f'PL{world_number}', command=partial(change_world, world_number)).grid(row=index, column=0)

        self.world_chooser_window.bind('<Leave>', on_leave)
        MyFunc.center(self.world_chooser_window, self.title_world)
        self.world_chooser_window.attributes('-alpha', 1.0)

    def world_number_change(self, *args) -> None:

        def on_focus_out(event) -> None:
            if settings['world_number'] != self.entries_content['world_number'].get():            
                self.world_number_input.unbind_all('<FocusOut>')
                self.entries_content['world_number'].trace_remove('write', self.world_number_trace)
                self.add_new_world_settings()
                self.world_number_trace = self.entries_content['world_number'].trace_add('write', self.world_number_change)

        if settings['world_number'] != self.entries_content['world_number'].get():
            self.world_number_input.bind('<FocusOut>', on_focus_out)


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
                    main_window.master.attributes('-alpha', 1.0)
                    settings['logged'] = True
                    return
        
        self.master = tk.Toplevel(borderwidth=1, relief='groove')
        self.master.overrideredirect(True)
        self.master.resizable(0, 0)
        self.master.attributes('-topmost', 1)
        
        self.custom_bar = ttk.Frame(self.master)
        self.custom_bar.grid(row=0, column=0, sticky=('N', 'S', 'E', 'W'))
        self.custom_bar.columnconfigure(3, weight=1)

        self.title_label = ttk.Label(self.custom_bar, text='Logowanie')
        self.title_label.grid(row=0, column=2, padx=5 , sticky='W')

        self.exit_button = ttk.Button(self.custom_bar, text='X', command=main_window.master.destroy)
        self.exit_button.grid(row=0, column=4, padx=(0, 5), pady=3, sticky='E')

        ttk.Separator(self.master, orient='horizontal').grid(row=1, column=0, sticky=('W', 'E'))
        
        self.content = ttk.Frame(self.master)
        self.content.grid(row=2, column=0, sticky=('N', 'S', 'E', 'W'))

        self.user_name = ttk.Label(self.content, text='Nazwa:')
        self.user_password = ttk.Label(self.content, text='Hasło:')
        self.register = ttk.Label(self.content, text='Nie posiadasz jeszcze konta?')

        self.user_name.grid(row=2, column=0, pady=4, padx=5, sticky='W')
        self.user_password.grid(row=3, column=0, pady=4, padx=5, sticky='W')
        self.register.grid(row=6, column=0, columnspan=2, pady=(4, 0), padx=5)

        self.user_name_input = ttk.Entry(self.content)
        self.user_password_input = ttk.Entry(self.content, show='*')

        self.user_name_input.grid(row=2, column=1, pady=(5, 5), padx=5)
        self.user_password_input.grid(row=3, column=1, pady=4, padx=5)

        self.remember_me = tk.StringVar()
        self.remember_me_button = ttk.Checkbutton(self.content, text='Zapamiętaj mnie', 
                                         variable=self.remember_me, onvalue=True, offvalue=False)
        self.remember_me_button.grid(row=4, columnspan=2, pady=4, padx=5, sticky='W')

        self.log_in_button = ttk.Button(self.content, text='Zaloguj', command=self.log_in)
        self.register_button = ttk.Button(self.content, text='Utwórz konto')

        self.log_in_button.grid(row=5, columnspan=2, pady=4, padx=5, sticky=('W', 'E'))
        self.register_button.grid(row=7, columnspan=2, pady=5, padx=5, sticky=('W', 'E'))

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
            main_window.master.attributes('-alpha', 1.0)


class JobsToDoWindow:   

    translate_tuples = (
            ('gathering', 'zbieractwo'),
            ('auto_farm', 'farmienie'),
            ('check_incoming_attacks', 'etykiety ataków'),
            ('premium_exchange', 'giełda premium')
        )

    def __init__(self) -> None:        
        self.master = tk.Toplevel()
        self.master.attributes('-alpha', 0.0)
        self.master.iconbitmap(default='icons//ikona.ico')        
        self.master.title('Tribal Wars 24/7')        
        self.master.overrideredirect(True)
        self.master.attributes('-topmost', 1)

        # main_frame -> custom_bar, content_frame
        self.main_frame = ttk.Frame(self.master, borderwidth=1, relief='groove')
        self.main_frame.grid(row=0, column=0, sticky=('N', 'S', 'E', 'W'))

        self.custom_bar = ttk.Frame(self.main_frame)
        self.custom_bar.grid(row=0, column=0, sticky=('N', 'S', 'E', 'W'))
        self.custom_bar.columnconfigure(3, weight=1)

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky=('N', 'S', 'E', 'W'))

        # custom_bar
        self.title_label = ttk.Label(self.custom_bar, text='Lista zadań')
        self.title_label.grid(row=0, column=1, padx=(5, 0) , sticky='W')

        self.time = tk.StringVar()
        self.title_timer = ttk.Label(self.custom_bar, textvariable=self.time)
        self.title_timer.grid(row=0, column=2, padx=5)

        self.photo = tk.PhotoImage(file='icons//minimize.png')
        self.minimize = self.photo.subsample(2, 2)

        self.minimize_button = ttk.Button(self.custom_bar, bootstyle='primary.Link.TButton', image=self.minimize, command=self.hide)
        self.minimize_button.grid(row=0, column=4, padx=(5, 0), pady=5, sticky='E')

        self.photo = tk.PhotoImage(file='icons//exit.png')
        self.exit = self.photo.subsample(8, 8)

        self.exit_button = ttk.Button(self.custom_bar, bootstyle='primary.Link.TButton', image=self.exit, command=self.master.destroy)
        self.exit_button.grid(row=0, column=5, padx=(0, 5), pady=3, sticky='E')      

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

        self.scrollable_window = ScrollableFrame(parent=self.content_frame)
        
        # def on_configure(event):
        #     # Update scrollregion after starting 'mainloop'
        #     # when all widgets are in canvas.
        #     self.canvas.configure(scrollregion=self.canvas.bbox('all'))

        # def _bound_to_mousewheel(self, event):
        #     self.canvas.bind_all("<MouseWheel>", lambda event: _on_mousewheel(self, event))

        # def _unbound_to_mousewheel(self, event):
        #     self.canvas.unbind_all("<MouseWheel>")

        # def _on_mousewheel(self, event):
        #     self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        # # --- Create self.canvas with scrollbar ---

        # self.canvas = tk.Canvas(self.content_frame)
        # self.canvas.grid(row=0, column=0, sticky='nsew')

        # self.scrollbar = ttk.Scrollbar(self.content_frame, command=self.canvas.yview)
        # self.scrollbar.grid(row=0, column=1, sticky='ns')

        # self.canvas.configure(yscrollcommand = self.scrollbar.set)
        # self.canvas.bind('<Enter>', lambda event: _bound_to_mousewheel(self, event))
        # self.canvas.bind('<Leave>', lambda event: _unbound_to_mousewheel(self, event))

        # # Update scrollregion after starting 'mainloop'
        # # when all widgets are in self.canvas.
        # self.canvas.bind('<Configure>', on_configure)

        # # --- Put frame in self.canvas ---

        # self.frame = ttk.Frame(self.canvas)
        # self.canvas.create_window((0, 0), window=self.frame)

        # --- Add widgets in self.frame ---      
        self.add_widgets_to_frame()
    
    def add_widgets_to_frame(self) -> None:
        """Add widgets to self.frame in self.canvas"""
        
        # Table description -> column names
        for col_index, col_name in zip(range(1, 4, 1), ('Świat', 'Zadanie', 'Data wykonania')):
            if col_name != 'Data wykonania':
                ttk.Label(self.scrollable_window.frame, text=col_name).grid(row=0, column=col_index, padx=10, pady=5)                
            else:
                ttk.Label(self.scrollable_window.frame, text=col_name).grid(row=0, column=col_index, padx=(10, 25), pady=5)                  
        
        # Create table with data of jobs to do
        for row_index, row in enumerate(main_window.to_do):  
            row_index += 1                    
            ttk.Label(self.scrollable_window.frame, text=f'{row_index}.').grid(row=row_index, column=0, padx=(25, 10), pady=5)            
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
                    ttk.Label(self.scrollable_window.frame, text=label_text).grid(row=row_index, column=col_index+1, padx=10, pady=5)                    
                else:
                    ttk.Label(self.scrollable_window.frame, text=label_text).grid(row=row_index, column=col_index+1, padx=(10, 25), pady=(5, 10))                    

        # Update canvas size depend on frame requested size
        # self.scrollable_window.frame.update()
        # if self.scrollable_window.frame.winfo_reqheight() <= 250:
        #     self.canvas['height'] = self.scrollable_window.frame.winfo_reqheight()
        # else:
        #     self.canvas['height'] = 250
        # self.canvas['width'] = self.scrollable_window.frame.winfo_reqwidth()

        # self.canvas.yview_moveto(0)

        self.scrollable_window.update_canvas(max_height=250)

    def update_widgets_in_frame(self) -> None:
        """Clear and than create new widgets in frame"""

        for widgets in self.scrollable_window.frame.winfo_children():
            widgets.destroy()            
        self.add_widgets_to_frame()


if __name__ == '__main__':    

    driver = None
    settings = MyFunc.load_settings()

    if settings['first_lunch']:
        MyFunc.first_app_lunch()

    main_window = MainWindow()
    style = ttk.Style(theme='dark')
    style.map('primary.Link.TButton', background=[('active', 'gray18')], bordercolor=[('active', '')])
    log_in_window = LogInWindow()

    main_window.master.mainloop()

    