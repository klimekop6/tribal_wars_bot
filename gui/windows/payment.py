import tkinter as tk
from typing import TYPE_CHECKING

import ttkbootstrap as ttk

from gui.functions import center
from gui.widgets.my_widgets import TopLevel

if TYPE_CHECKING:
    from gui.windows.main import MainWindow


class PaymentWindow:
    def __init__(self, parent: "MainWindow") -> None:
        if hasattr(parent, "payment_window"):
            if parent.payment_window.winfo_exists():
                parent.payment_window.lift()
                return

        self.master = parent.payment_window = TopLevel(title_text="Tribal Wars Bot")
        self.master.geometry("555x505")

        self.text = ttk.Text(
            master=self.master.content_frame,
            wrap="word",
        )
        self.text.grid(row=0, column=0, sticky=ttk.NSEW)
        self.text.insert("1.0", "Dostępne pakiety:\n", "bold_text")
        self.text.insert("2.0", "- 30zł za jeden miesiąc\n")
        self.text.insert("3.0", "- 55zł za dwa miesiące 60zł oszczędzasz 5zł\n")
        self.text.insert("4.0", "- 75zł za trzy miesiące 90zł oszczędzasz 15zł\n")
        self.text.insert("5.0", "Dostępne metody płatności:\n", "bold_text")
        self.text.insert(
            "6.0", "- blik na numer: 511 163 955 (nazwa odbiorcy: Klemens)\n"
        )
        self.text.insert(
            "7.0", "- przelew na numer: 95 1050 1025 1000 0097 5211 9777\n"
        )
        self.text.insert(
            "8.0",
            f'W tytule blika/przelewu należy wpisać swój login "{parent.user_data["user_name"]}"\n',
            "bold_text",
        )
        self.text.insert("9.0", "Czas oczekiwania:\n", "bold_text")
        self.text.insert("10.0", "Blik\n", "bold_text")
        self.text.insert("11.0", "- przeważnie w ciągu kilku godzin\n")
        self.text.insert("12.0", "- maksymalnie jeden dzień\n")
        self.text.insert("13.0", "Przelew\n", "bold_text")
        self.text.insert("14.0", "- przeważnie w ciągu jednego dnia *\n")
        self.text.insert(
            "15.0",
            "* Wyjątek stanowią weekendy i dni ustawowo wolne od pracy jako, że w te dni "
            "banki nie realizują przelewów. W takim przypadku w celu przyspieszenia aktywacji "
            "wystarczy wysłać potwierdzenie przelewu na adres e-mail k.spec@tuta.io. "
            "Na tej podstawie mogę dokonać aktywacji konta niezwłocznie po odczytaniu wiadomości.",
        )

        self.copy_icon = tk.PhotoImage(file="icons//copy.png")

        def copy_acc_number() -> None:
            self.text.clipboard_clear()
            self.text.clipboard_append("95 1050 1025 1000 0097 5211 9777")
            self.text.config(state="normal")
            self.text.insert("7.end", "skopiowano do schowka")
            self.text.config(state="disabled")

            def delete_extra_text() -> None:
                self.text.config(state="normal")
                self.text.delete("7.53", "7.end")
                self.text.config(state="disabled")

            self.text.after(ms=3000, func=delete_extra_text)

        copy_button = ttk.Button(
            master=self.text,
            image=self.copy_icon,
            style="copy.primary.Link.TButton",
            command=copy_acc_number,
        )
        copy_button.bind("<Enter>", lambda _: self.text.config(cursor=""))
        copy_button.bind("<Leave>", lambda _: self.text.config(cursor="xterm"))
        self.text.window_create("7.end", window=copy_button, padx=4)

        self.text.tag_add("account_number", "7.20", "8.0-1c")
        self.text.tag_add("italic_text", "15.0", "end")
        self.text.tag_add("indent_text", "1.0", "end")
        self.text.tag_add("first_line", "1.0", "1.end -1c")
        self.text.tag_add("last_line", "end -1 lines", "end")
        self.text.tag_add("strike", "3.23", "3.27", "4.24", "4.28")

        self.text.tag_config(
            "bold_text",
            font=("TkTextFont", 11, "bold"),
            lmargin1=16,
            spacing1=16,
            spacing3=3,
        )
        self.text.tag_config(
            "italic_text",
            font=("TkTextFont", 10, "italic"),
            lmargin1=16,
            lmargin2=25,
            spacing1=16,
        )
        self.text.tag_config("indent_text", lmargin1=25, rmargin=16)
        self.text.tag_config("first_line", spacing1=10)
        self.text.tag_config("last_line", spacing3=10)
        self.text.tag_config("strike", overstrike=True)

        self.text.tag_raise("bold_text", "indent_text")
        self.text.tag_raise("italic_text", "indent_text")

        self.text.config(state="disabled")

        center(window=self.master, parent=parent.master)
        self.master.attributes("-alpha", 1.0)
