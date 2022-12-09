from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap import localization

from config import APP_VERSION
from my_widgets import CollapsingFrame, ScrollableFrame, Text

if TYPE_CHECKING:
    from app_gui.windows.main_window import MainWindow

translate = localization.MessageCatalog.translate


class Home(ScrollableFrame):
    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ):
        self.parent = parent

        super().__init__(master=parent, padding=[10, 0, 10, 0])
        self.place(rely=0.0, relheight=1.0, relwidth=1.0)
        self.columnconfigure(0, weight=1)

        ttk.Label(
            self,
            text=f"{translate('Application version')} {APP_VERSION}",
            font=("TkFixedFont", 11),
        ).grid(row=0, column=0, sticky=ttk.W)

        # Current changes
        ttk.Label(
            self, text=translate("Current changes"), font=("TkFixedFont", 11)
        ).grid(row=1, column=0, pady=(35, 15), sticky=ttk.W)

        cf_current_changes = CollapsingFrame(self)
        cf_current_changes.grid(row=2, column=0, sticky=ttk.EW)

        text = Text(cf_current_changes)

        text.add("Poprawki\n", "h1")
        text.add(
            "- Poprawiono wyliczane prędkości przemarszu wojsk dla niestandardowych ustawień świata.\n"
        )

        cf_current_changes.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.80",
            bootstyle="dark",
        )

        # Previous changes
        ttk.Label(self, text=translate("Last changes"), font=("TkFixedFont", 11)).grid(
            row=5, column=0, pady=(25, 15), sticky=ttk.W
        )

        # 1.0.79
        cf_last_changes_1_0_79 = CollapsingFrame(self)
        cf_last_changes_1_0_79.grid(row=11, column=0, pady=(0, 5), sticky=ttk.EW)

        text = Text(cf_last_changes_1_0_79)

        text.add("Nowość\n", "h1")
        text.add(
            "- Utworzono wyjątek w trakcie dodawania światów dla globalnych serwerów turniejowych. "
            "Serwer aktualnego turnieju to tribalwars.net a numer świata to c4. Uwaga, świat nie był testowany. "
            "W razie jakiś błędów/problemów dajcie znać na discordzie k.spec#9583 lub pod adres k.spec@tuta.io \n"
        )

        cf_last_changes_1_0_79.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.79",
            bootstyle="dark",
        )

        # 1.0.78
        cf_last_changes_1_0_78 = CollapsingFrame(self)
        cf_last_changes_1_0_78.grid(row=12, column=0, pady=(0, 5), sticky=ttk.EW)

        text = Text(cf_last_changes_1_0_78)

        text.add("Poprawki\n", "h1")
        text.add(
            "- Naprawiono błąd związany z automatycznym farmieniem. Błąd pojawiał "
            "się tylko w tedy gdy w wioskach nie było żadnych wojsk do wysłania.\n"
        )

        cf_last_changes_1_0_78.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.78",
            bootstyle="dark",
        )

        # 1.0.77
        cf_last_changes_1_0_77 = CollapsingFrame(self)
        cf_last_changes_1_0_77.grid(row=13, column=0, pady=(0, 5), sticky=ttk.EW)

        text = Text(cf_last_changes_1_0_77)

        text.add("Poprawki\n", "h1")
        text.add(
            "- Naprawiono błąd blokujący zbieractwo dla nowych graczy (dotyczy tylko tych którzy utworzyli nowe konta w ostatniej wersji 1.7.6)\n"
        )

        cf_last_changes_1_0_77.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.77",
            bootstyle="dark",
        )

        # 1.0.76
        cf_last_changes_1_0_76 = CollapsingFrame(self)
        cf_last_changes_1_0_76.grid(row=14, column=0, pady=(0, 5), sticky=ttk.EW)

        text = Text(cf_last_changes_1_0_76)
        text.add("Nowości\n", "h1")
        text.add(
            "- W zbieractwie dodano nową funkcję do włączenia której zadaniem jest "
            "inteligente pomijanie poziomów zbieractwa w celu uzyskania maksymalnej "
            "efektywności zbieranych surowców.\n"
        )
        text.add("Poprawki\n", "h1")
        text.add(
            "- Zbieractwo działa teraz identycznie do legalnego skryptu znajdującego "
            "się w skryptotece plemion. Dodatkowo wojska nie będą ponownie wysyłane "
            "zawsze sekundę po ich powrocie a w przedziale od 5 do 30 sekund później. "
            "Celem jest upodobnienie działań do rzeczywistego użytkownika. "
        )

        cf_last_changes_1_0_76.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.76",
            bootstyle="dark",
        )

        # 1.0.75
        cf_last_changes_1_0_75 = CollapsingFrame(self)
        cf_last_changes_1_0_75.grid(row=15, column=0, pady=(0, 5), sticky=ttk.EW)

        text = Text(cf_last_changes_1_0_75)
        text.add("Nowości\n", "h1")
        text.add(
            "- Wszystkie przyciski których zadaniem było zamknięcie lub usunięcie "
            "będą podświetlane na czerwonym tle po najechaniu myszką.\n"
        )
        text.add(
            "- Dodano w ustawieniach opcję wyłączenia funkcji oszczędzania energii "
            "przez przeglądarkę google Chrome. Więcej informacji znajduję się po "
            "najechaniu na ikonę znaku zapytania naprzeciwko nowego pola ustawień.\n"
        )
        text.add("Poprawki\n", "h1")
        text.add(
            "- Naprawiono tworzenie etykiet ataków na światach z wieżą strażniczą.\n"
        )
        text.add(
            "- Skrócono o połowę czas potrzebny do wykrycia i ponownego uruchomienia "
            "zamkniętego okna przeglądarki.\n"
        )
        text.add(
            "- Skompresowano wszystkie wykorzystywane ikony w aplikacji w celu "
            "szybszego pobierania i uruchamiania aplikacji a także nieznacznie "
            "mniejszego zużycia pamięci ram.\n"
        )

        cf_last_changes_1_0_75.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.75",
            bootstyle="dark",
        )

        # Incoming changes

        ttk.Label(
            self, text=translate("Incoming changes"), font=("TkFixedFont", 11)
        ).grid(row=25, column=0, pady=(25, 15), sticky=ttk.W)

        cf_incoming_changes = CollapsingFrame(self)
        cf_incoming_changes.grid(row=26, column=0, pady=(0, 20), sticky=ttk.EW)

        text = Text(cf_incoming_changes)
        text.add("Nowości\n", "h1")
        text.add("- Dodano nową funkcję uniki.\n")
        text.add("- Dodano nową funkcję kontratak.\n")
        text.add("- Dodano nową funkcję menadżer konta.\n")

        cf_incoming_changes.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.1.XX",
            bootstyle="dark",
        )

        self.bind("<Map>", lambda _: [self.bind("<Configure>", self._on_configure)])

    def _on_configure(self, event=None):

        self.unbind("<Configure>")
        if self._measures() != (1.0, 1.0):
            self.configure(padding=(10, 0, 20, 0))
        else:
            self.configure(padding=(10, 0, 10, 0))

        self.update_idletasks()
        super()._on_configure()
        self.bind("<Configure>", self._on_configure)
