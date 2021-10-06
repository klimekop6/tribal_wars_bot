from tkinter import *
from tkinter.ttk import *
from ttkbootstrap import Style
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import pyodbc
import time
import bot_functions

# context manager
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

    def current_time() -> str:
        return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())

    def if_paid(date: str) -> bool:
        if time.strptime(MyFunc.current_time(), '%d/%m/%Y %H:%M:%S') > time.strptime(date + ' 23:59:59', '%Y-%m-%d %H:%M:%S'):
            return False
        return True
    
    def load_settings() -> dict:
        try:
            f = open('settings.json')
            settings = json.load(f)
        except FileNotFoundError:
            f = open('settings.json', 'w')
            json.dump({}, f)
            settings = {}
        finally:
            f.close()            
        return settings

    def center(window) -> None:
        """ place window in the center of a screen """

        window.update_idletasks()
        window.geometry(f'+{int(window.winfo_screenwidth()/2 - window.winfo_reqwidth()/2)}'
                             f'+{int(window.winfo_screenheight()/2 - window.winfo_reqheight()/2)}')

    def custom_error(self, message: str) -> None:
        
        self.master = Toplevel(borderwidth=1, relief='groove')
        self.master.overrideredirect(True)
        self.master.attributes('-topmost', 1)        
        self.master.bell()

        #title_label = Label(self.master, text=title).grid(row=0, column=0, padx=5, pady=5)
        self.message_label = Label(self.master, text=message)
        self.message_label.grid(row=1, column=0, padx=5, pady=5)

        self.ok_button = Button(self.master, text='ok', command=self.master.destroy)
        self.ok_button.grid(row=2, column=0, pady=(5,8))
     
        self.message_label.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'message_label'))
        self.ok_button.focus_force()
        self.ok_button.bind('<Return>', lambda event: self.master.destroy())
        MyFunc.center(self.master)

    def chrome_profile_path() -> None:
        """ wyszukuję i zapisuje w ustawieniach aplikacji aktualną ścierzkę do profilu użytkownika przeglądarki chrome """

        driver = webdriver.Chrome('chromedriver.exe')
        driver.get('chrome://version')
        path = driver.find_element_by_xpath('//*[@id="profile_path"]').text
        path = path[:path.find('Temp\\')] + 'Google\\Chrome\\User Data'
        settings['path'] = path

        with open('settings.json', 'w') as settings_json_file:
            json.dump(settings, settings_json_file)

    def run_driver() -> None:
        """ uruchamia sterownik i przeglądarkę google chrome """

        global driver
        chrome_options = Options()
        chrome_options.add_argument('user-data-dir=' + settings['path']) 
        driver = webdriver.Chrome('chromedriver.exe', options=chrome_options)
        driver.maximize_window()

    def save_entry_to_settings(entries: dict) -> None:

        for key, value in entries.items():
            settings[key] = value.get()
        with open('settings.json', 'w') as settings_json_file:
            json.dump(settings, settings_json_file)

    def fill_entry_from_settings(entries: dict) -> None:

        for key in entries:
            if key in settings:
                if settings[key]:
                    entries[key].set(settings[key])
                else:
                    entries[key].set(0)

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

    def change_state(parent, value, entries_content, reverse=False, *ommit) -> None:

        def disableChildren(parent):
            if not parent.winfo_children():
                parent.config(state='disabled')
            for child in parent.winfo_children():
                wtype = child.winfo_class()
                if wtype not in ('Frame','Labelframe'):
                    if child not in ommit:
                        child.configure(state='disable')
                else:
                    disableChildren(child)

        def enableChildren(parent):
            if not parent.winfo_children():
                parent.config(state='normal')
            for child in parent.winfo_children():
                wtype = child.winfo_class()
                if wtype not in ('Frame','Labelframe'):
                    if child not in ommit:
                        child.configure(state='normal')
                else:
                    enableChildren(child)

        if not isinstance(value, int): 
            value = int(entries_content[value].get())

        if not reverse:
            if value:
                disableChildren(parent)
            else:
                enableChildren(parent)
        else:
            if value:
                enableChildren(parent)
            else:
                disableChildren(parent)

    def change_state_on_settings_load(parent, name, entries_content, reverse=False, *ommit) -> None:
        if name in settings:  
            if settings[name] == '':
                return
            if int(settings[name]) or reverse:
                MyFunc.change_state(parent, int(settings[name]), entries_content, reverse, *ommit) 

class MainWindow:
    
    entries_content = {}
    elements_state = []

    def __init__(self) -> None:
        self.master = Tk()
        self.master.attributes('-alpha', 0.0)
        self.master.iconbitmap(default='ikona.ico')        
        self.master.title('Tribal Wars 24/7')        
        self.master.eval('tk::PlaceWindow . center')  
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
        self.title_label.grid(row=0, column=2, padx=5 , sticky=W)

        self.photo = PhotoImage(file='minimize.png')
        self.minimize = self.photo.subsample(2, 2)

        self.minimize_button = Button(self.custom_bar, style='primary.Link.TButton', image=self.minimize, command=self.hide)
        self.minimize_button.grid(row=0, column=3, padx=(5, 0), pady=5, sticky=E)

        self.photo = PhotoImage(file='exit3.png')
        self.exit = self.photo.subsample(8, 8)

        self.exit_button = Button(self.custom_bar, style='primary.Link.TButton', image=self.exit, command=self.master.destroy)
        self.exit_button.grid(row=0, column=4, padx=(0, 5), pady=3, sticky=E)      

        self.custom_bar.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'custom_bar'))
        self.title_label.bind('<Button-1>', lambda event: MyFunc.get_pos(self, event, 'title_label'))

        # content_frame

        # notebook with frames 
        n = Notebook(self.content_frame)
        n.grid(row=1, column=0, padx=5, pady=5, sticky=(N, S, E, W))
        f1 = Frame(n)
        f2 = Frame(n)
        f3 = Frame(n)
        f4 = Frame(n)
        n.add(f1, text='Farma')
        n.add(f2, text='Two')
        n.add(f3, text='Three')
        n.add(f4, text='Ustawienia')        
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
        
        self.entries_content['active_A'] = StringVar()
        self.active_A = Checkbutton(A, text='Aktywuj szablon', 
                                    variable=self.entries_content['active_A'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: (MyFunc.change_state(*self.elements_state[0]), 
                                    self.attacks_number_input_A.config(state='disabled') 
                                    if int(self.entries_content['active_A'].get()) and 
                                     int(self.entries_content['max_attacks_A'].get()) else None))
        self.active_A.grid(row=0, column=0, columnspan=2, padx=5, pady=(20, 10))
        self.elements_state.append([A, 'active_A', self.entries_content, True, self.active_A])
        
        self.wall = Label(A, text='Poziom muru')
        self.wall.grid(row=1, column=0, pady=10, padx=5, sticky=W)

        self.min_wall_level = Label(A, text='Min')
        self.min_wall_level.grid(row=2, column=0, pady=5, padx=(25, 5), sticky=W)

        self.entries_content['min_wall_A'] = StringVar()
        self.min_wall_level_input = Entry(A, width=5, textvariable=self.entries_content['min_wall_A'], justify='center')
        self.min_wall_level_input.grid(row=2, column=1, pady=5, padx=(5, 25), sticky=E)

        self.max_wall_level = Label(A, text='Max')
        self.max_wall_level.grid(row=3, column=0, pady=5, padx=(25, 5), sticky=W)

        self.entries_content['max_wall_A'] = StringVar()
        self.max_wall_level_input_A = Entry(A, width=5, textvariable=self.entries_content['max_wall_A'], justify='center')
        self.max_wall_level_input_A.grid(row=3, column=1, pady=5, padx=(5, 25), sticky=E)

        self.attacks = Label(A, text='Wysyłka ataków')
        self.attacks.grid(row=4, column=0, pady=10, padx=5, sticky=W)        

        self.entries_content['max_attacks_A'] = StringVar()
        self.max_attacks_A = Checkbutton(A, text='Maksymalna ilość', 
                                    variable=self.entries_content['max_attacks_A'], 
                                    onvalue=True, offvalue=False, 
                                    command=lambda: MyFunc.change_state(*self.elements_state[1]))
        self.max_attacks_A.grid(row=5, column=0, pady=5, padx=(25, 5), sticky=W)

        self.attacks = Label(A, text='Ilość ataków')
        self.attacks.grid(row=6, column=0, pady=(5, 10), padx=(25, 5), sticky=W)

        self.entries_content['attacks_number_A'] = StringVar()
        self.attacks_number_input_A = Entry(A, width=5, textvariable=self.entries_content['attacks_number_A'], justify='center')
        self.attacks_number_input_A.grid(row=6, column=1, pady=(5, 10), padx=(5, 25), sticky=E)
        self.elements_state.append([self.attacks_number_input_A, 'max_attacks_A', self.entries_content])
        #endregion
        
        # Szablon B
        #region
        B.columnconfigure(0, weight=1)
        B.columnconfigure(1, weight=1)
        
        self.entries_content['active_B'] = StringVar()
        self.active_B = Checkbutton(B, text='Aktywuj szablon', 
                                    variable=self.entries_content['active_B'], 
                                    onvalue=True, offvalue=False,
                                    command=lambda: (MyFunc.change_state(*self.elements_state[2]), 
                                    self.attacks_number_input_B.config(state='disabled') 
                                    if int(self.entries_content['active_B'].get()) and 
                                    int(self.entries_content['max_attacks_B'].get()) else None))
        self.active_B.grid(row=0, column=0, columnspan=2, padx=5, pady=(20, 10))
        self.elements_state.append([B, 'active_B', self.entries_content, True, self.active_B])
        
        self.wall = Label(B, text='Poziom muru')
        self.wall.grid(row=1, column=0, pady=10, padx=5, sticky=W)

        self.min_wall_level = Label(B, text='Min')
        self.min_wall_level.grid(row=2, column=0, pady=5, padx=(25, 5), sticky=W)

        self.entries_content['min_wall_B'] = StringVar()
        self.min_wall_level_input_B = Entry(B, width=5, textvariable=self.entries_content['min_wall_B'], justify='center')
        self.min_wall_level_input_B.grid(row=2, column=1, pady=5, padx=(5, 25), sticky=E)

        self.max_wall_level = Label(B, text='Max')
        self.max_wall_level.grid(row=3, column=0, pady=5, padx=(25, 5), sticky=W)

        self.entries_content['max_wall_B'] = StringVar()
        self.max_wall_level_input_B = Entry(B, width=5, textvariable=self.entries_content['max_wall_B'], justify='center')
        self.max_wall_level_input_B.grid(row=3, column=1, pady=5, padx=(5, 25), sticky=E)

        self.attacks = Label(B, text='Wysyłka ataków')
        self.attacks.grid(row=4, column=0, pady=10, padx=5, sticky=W)        

        self.entries_content['max_attacks_B'] = StringVar()
        self.max_attacks_B = Checkbutton(B, text='Maksymalna ilość', 
                                    variable=self.entries_content['max_attacks_B'], 
                                    onvalue=True, offvalue=False, 
                                    command=lambda: MyFunc.change_state(*self.elements_state[3]))
        self.max_attacks_B.grid(row=5, column=0, pady=5, padx=(25, 5), sticky=W)

        self.attacks = Label(B, text='Ilość ataków')
        self.attacks.grid(row=6, column=0, pady=(5, 10), padx=(25, 5), sticky=W)

        self.entries_content['attacks_number_B'] = StringVar()
        self.attacks_number_input_B = Entry(B, width=5, textvariable=self.entries_content['attacks_number_B'], justify='center')
        self.attacks_number_input_B.grid(row=6, column=1, pady=(5, 10), padx=(5, 25), sticky=E)
        self.elements_state.append([self.attacks_number_input_B, 'max_attacks_B', self.entries_content])
        #endregion        
        
        # Szablon C
        #region
        #endregion

        # f2 -> 'Two'
        f2.columnconfigure(0, weight=1)

        Label(f2, compound=LEFT, text='adin dwa tri', image=self.photo).grid(row=0, column=0)

        # f3 -> 'Three'
        f3.columnconfigure(0, weight=1)

        # f4 -> 'Ustawienia'
        f4.columnconfigure(0, weight=1)
        f4.columnconfigure(1, weight=1)


        self.world_number = Label(f4, text='Numer świata')
        self.world_number.grid(row=0, column=0, padx=5, pady=(10, 5), sticky=W)
        
        self.entries_content['world'] = StringVar()
        self.world_number_input = Entry(f4, textvariable=self.entries_content['world'], width=3)
        self.world_number_input.grid(row=0, column=1, padx=5, pady=(10, 5))

        self.entries_content['auto_farm'] = StringVar()
        self.auto_farm = Checkbutton(f4, text='Automatyczne farmienie', 
                                    variable=self.entries_content['auto_farm'], 
                                    onvalue=True, offvalue=False)
        self.auto_farm.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=W)

        # content_frame
        self.save_button = Button(self.content_frame, text='zapisz', command=lambda: MyFunc.save_entry_to_settings(self.entries_content))
        self.save_button.grid(row=2, column=0, padx=5, pady=5, sticky=(W, E))

        self.run_button = Button(self.content_frame, text='uruchom', command=self.run)
        self.run_button.grid(row=3, column=0, padx=5, pady=5, sticky=(W, E))

        # other things
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

    def run(self):
        MyFunc.run_driver()
        bot_functions.log_in(driver, settings)

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

        self.remember_me = IntVar(0)
        self.remember_me_button = Checkbutton(self.content, text='Zapamiętaj mnie', 
                                         variable=self.remember_me, onvalue=1, offvalue=0)
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

if __name__ == '__main__':
    
    settings = MyFunc.load_settings()
    driver = None
    
    main_window = MainWindow()
    style = Style(theme='darkly')
    style.map('primary.Link.TButton', background=[('active', 'gray18')], bordercolor=[('active', '')])
    style.theme_use()
    log_in_window = LogInWindow()

    main_window.master.mainloop()