from tkinter import *
from tkinter.ttk import *
from ttkbootstrap import Style
import tkinter.messagebox
import json
import pyodbc
import time

# context manager
class DataBaseConnection:

    def __init__(self) -> None:
        self.cnxn = None
        self.cursor = None

    def __enter__(self):
        self.cnxn = pyodbc.connect('''DRIVER={ODBC Driver 17 for SQL Server};
                                     SERVER=***REMOVED***;
                                     DATABASE=Plemiona;
                                     UID=***REMOVED***;
                                     PWD=***REMOVED***''')
        self.cursor = self.cnxn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_value, exc_tracebac):
        self.cnxn.commit()
        self.cnxn.close()

class MyFunc:

    def current_time() -> str:
        return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())

    def if_paid(date: str) -> bool:
        if  time.strptime(MyFunc.current_time(), '%d/%m/%Y %H:%M:%S') > time.strptime(date + ' 23:59:59', '%Y-%m-%d %H:%M:%S'):
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

    def error(self, title: str, message: str) -> None:
        self.master.attributes('-topmost', 0)
        tkinter.messagebox.showerror(title=title, message=message)                
        self.master.attributes('-topmost', 1)

class MainWindow:

    def __init__(self) -> None:
        self.master = Tk()
        self.master.attributes('-alpha', 0.0)
        self.master.iconbitmap(default='ikona.ico')        
        self.master.title('Tribal Wars 24/7')        
        self.master.eval('tk::PlaceWindow . center')  
        self.master.overrideredirect(True)      

        n = Notebook(self.master)
        n.grid(row=0, column=0, padx=5, pady=5, sticky=(N, S, E, W))
        f1 = Frame(n)
        f2 = Frame(n)
        f3 = Frame(n)
        f4 = Frame(n)
        n.add(f1, text='One')
        n.add(f2, text='Two')
        n.add(f3, text='Three')
        n.add(f4, text='Four')
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        self.exit_button = Button(self.master, text='zamknij', command=self.master.destroy)
        self.exit_button.grid(row=1, column=0, padx=5, pady=5, sticky=(W, E))

        self.test_button = Button(self.master, text='test', command=self.hide)
        self.test_button.grid(row=2, column=0, padx=5, pady=5, sticky=(W, E))

        self.master.attributes('-alpha', 1.0)
        self.master.withdraw()          
    
    def hide(self):
        self.master.attributes('-alpha', 0.0)
        self.master.overrideredirect(False)
        self.master.iconify()
        def show(event=None):
            self.master.overrideredirect(True)
            self.master.attributes('-alpha', 1.0)
        self.test_button.bind("<Map>", show)    

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
                    tkinter.messagebox.showerror(title='Błąd', message='Automatyczne logowanie nie powiodło się')
                elif not MyFunc.if_paid(str(row[5])):
                    tkinter.messagebox.showerror(title='Błąd', message='Ważność konta wygasła')                
                elif row[6]:
                    tkinter.messagebox.showerror(title='Błąd', message='Konto jest już obecnie w użyciu')                
                else:                    
                    main_window.master.deiconify()
                    settings['logged'] = True
                    return
        
        self.master = Toplevel()
        self.master.geometry(f'+{int(main_window.master.winfo_screenwidth()/2 - self.master.winfo_reqwidth()/2)}'
                             f'+{int(main_window.master.winfo_screenheight()/2 - self.master.winfo_reqheight()/2)}')
        self.master.overrideredirect(True)
        self.master.resizable(0, 0)
        self.master.attributes('-topmost', 1)
        
        self.custom_bar = Frame(self.master)
        self.custom_bar.grid(row=0, column=0, sticky=(N, S, E, W))
        self.custom_bar.columnconfigure(3, weight=1)

        self.title_label = Label(self.custom_bar, text='Logowanie')
        self.title_label.grid(row=0, column=2, padx=5 , sticky=W)

        exit_button = Button(self.custom_bar, text='X', command=main_window.master.destroy)
        exit_button.grid(row=0, column=4, padx=(0, 5), pady=3, sticky=E)

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
        self.custom_bar.bind('<Button-1>', self.get_pos)
        self.title_label.bind('<Button-1>', self.get_pos)
    
    def log_in(self, event=None):
        with DataBaseConnection() as cursor:            
            cursor.execute("SELECT * FROM Konta_Plemiona WHERE UserName='" 
                            + self.user_name_input.get() 
                            + "' AND Password='" 
                            + self.user_password_input.get() 
                            + "'")
            row = cursor.fetchone()
            if not row:                
                MyFunc.error(self, title='Błąd', message='Wprowadzono nieprawidłowe dane')
                return
            if not MyFunc.if_paid(str(row[5])):
                MyFunc.error(self, title='Błąd', message='Ważność konta wygasła')
                return
            if row[6]:
                MyFunc.error(self, title='Błąd', message='Konto jest już obecnie w użyciu')
                return

        if self.remember_me.get():
            settings['user_name'] = self.user_name_input.get()
            settings['user_password'] = self.user_password_input.get()
            with open('settings.json', 'w') as settings_json_file:
                json.dump(settings, settings_json_file)
        
        self.master.destroy() 
        main_window.master.deiconify()
        settings['logged'] = True

    def get_pos(self, event):
        xwin = self.master.winfo_x()
        ywin = self.master.winfo_y()
        startx = event.x_root
        starty = event.y_root

        ywin = ywin - starty
        xwin = xwin - startx

        def move_window(event):
            self.master.geometry(f"+{event.x_root + xwin}+{event.y_root + ywin}")
        startx = event.x_root
        starty = event.y_root

        self.custom_bar.bind('<B1-Motion>', move_window)
        self.title_label.bind('<B1-Motion>', move_window)

if __name__ == '__main__':
    
    settings = MyFunc.load_settings()

    main_window = MainWindow()
    style = Style(theme='darkly')
    style.theme_use()
    log_in_window = LogInWindow()
    
    main_window.master.mainloop()