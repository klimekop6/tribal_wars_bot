from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap import localization

from app.config import APP_VERSION
from gui.widgets.my_widgets import CollapsingFrame, ScrollableFrame, Text

if TYPE_CHECKING:
    from gui.windows.main import MainWindow

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

        text.add("Nowość\n", "h1")
        text.add(
            "- Dodano podgląd pozostałej liczby nawrotek wysyłanych ataków z planera.\n"
        )
        text.add("Poprawki\n", "h1")
        text.add(
            "- Naprawiono błąd który powodował wyświetlenie okna zmiany światów za oknem głównym aplikacji.\n"
        )
        text.add(
            "- Pole wyboru celu ostrzału katapult w planerze będzie wyłączone w przypadku zaznaczenia 'Wsparcie' zamiast 'Atak'.\n"
        )
        text.add(
            "- Naprawiono brak zmiany kursora myszki po najechaniu na pola do wprowadzania liczb lub tekstu.\n"
        )

        cf_current_changes.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.85",
            bootstyle="dark",
        )

        # Previous changes
        ttk.Label(self, text=translate("Last changes"), font=("TkFixedFont", 11)).grid(
            row=5, column=0, pady=(25, 15), sticky=ttk.W
        )

        # 1.0.84
        cf_last_changes_1_0_84 = CollapsingFrame(self)
        cf_last_changes_1_0_84.grid(row=14, column=0, pady=(0, 5), sticky=ttk.EW)

        text = Text(cf_last_changes_1_0_84)

        text.add("Hotfix\n", "h1")
        text.add(
            "- Porawka dotyczy problemów z captchą. Dnia 27.12.2022 wystąpiła awaria u usługodawcy "
            "'https://anycaptcha.com/' który dotychczas odpowiadał za podsyłanie rozwiązanych captchy. "
            "W związku z powyższym postanowiłem zmienić usługodawcę na 'https://2captcha.com/' który powinien "
            "w teori zaoferować lepszą jakość usługi."
        )

        cf_last_changes_1_0_84.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.84",
            bootstyle="dark",
        )

        # 1.0.83
        cf_last_changes_1_0_83 = CollapsingFrame(self)
        cf_last_changes_1_0_83.grid(row=15, column=0, pady=(0, 5), sticky=ttk.EW)

        text = Text(cf_last_changes_1_0_83)

        text.add("Poprawki\n", "h1")
        text.add("- Naprawiono etykiety ataków na światach specjalnych\n")
        text.add(
            "- Naprawiono limit czasowy przemarszu wysyłanych jednostek w dodatkowych ustawieniach farmy "
            "na światach specjalnych\n"
        )
        text.add(
            "- Dodano wyjątek dla wyślij wszystkie w przypadku wybrania wsparcia i rycerza jako "
            "najwolniejszej jednostki. Wszystkie pozostałe jednostki będą prawidłowo uwzględnione "
            "zgodnie z pozostałymi ustawieniami tj. wybierz tylko offensywne/deffensywne jednostki.\n"
        )
        text.add(
            "- Poprawiono stackowanie się okien bota (kolejność okien na wierzchu) w przypadku przełączania "
            "się pomiędzy aplikacjami w systemie lub ich zamykania/otwierania/minimalizowania.\n"
        )

        cf_last_changes_1_0_83.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.83",
            bootstyle="dark",
        )

        # 1.0.82
        cf_last_changes_1_0_82 = CollapsingFrame(self)
        cf_last_changes_1_0_82.grid(row=16, column=0, pady=(0, 5), sticky=ttk.EW)

        text = Text(cf_last_changes_1_0_82)

        text.add("Poprawki\n", "h1")
        text.add(
            "- Poprawiono dostrzeżone błędy w trakcie korzystania z funkcji "
            'nawrotek ("Powtórz atak po powrocie jednostek").\n'
        )

        cf_last_changes_1_0_82.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.82",
            bootstyle="dark",
        )

        # 1.0.81
        cf_last_changes_1_0_81 = CollapsingFrame(self)
        cf_last_changes_1_0_81.grid(row=17, column=0, pady=(0, 5), sticky=ttk.EW)

        text = Text(cf_last_changes_1_0_81)

        text.add("Poprawki\n", "h1")
        text.add(
            "- Poprawka dotyczy uwzględnienia różnicy czasu lokalnego ustawionego w systemie a "
            "czasu gry na serwerze. Od teraz nie powinno już być problemów z planerem bez względu na "
            "różnice w strefach czasowych.\n"
        )

        cf_last_changes_1_0_81.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.81",
            bootstyle="dark",
        )

        # 1.0.80
        cf_last_changes_1_0_80 = CollapsingFrame(self)
        cf_last_changes_1_0_80.grid(row=18, column=0, pady=(0, 5), sticky=ttk.EW)

        text = Text(cf_last_changes_1_0_80)

        text.add("Poprawki\n", "h1")
        text.add(
            "- Poprawiono wyliczane prędkości przemarszu wojsk dla niestandardowych ustawień świata.\n"
        )

        cf_last_changes_1_0_80.add(
            child=text.frame,
            title=f"{translate('Changes in patch')} 1.0.80",
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
