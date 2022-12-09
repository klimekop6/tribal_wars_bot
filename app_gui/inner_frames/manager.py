import threading
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from selenium import webdriver
from selenium.webdriver.common.by import By
from ttkbootstrap import localization

import app_functions
from bot_functions import game_data
from gui_functions import custom_error
from my_widgets import Label, ScrollableFrame

if TYPE_CHECKING:
    from app_gui.windows.main_window import MainWindow

translate = localization.MessageCatalog.translate


class Manager(ScrollableFrame):
    def __init__(
        self,
        parent: ttk.Frame,
        main_window: "MainWindow",
        entries_content: dict,
        settings: dict,
    ):
        super().__init__(parent, max_height=True)

        self.main_window = main_window
        self.settings = settings

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        manager = entries_content["manager"] = {}

        notebook = ttk.Notebook(self)
        notebook.grid(row=0, column=0, padx=5, pady=(0, 5), sticky=ttk.NSEW)

        self.nb_army = ScrollableFrame(notebook)
        self.nb_buildings = ScrollableFrame(notebook)
        self.nb_tech = ScrollableFrame(notebook)

        notebook.add(self.nb_army.container, text=translate("Army"))
        notebook.add(self.nb_buildings.container, text=translate("Buildings"))
        notebook.add(self.nb_tech.container, text=translate("Technology"))

        settings.setdefault("manager", {})
        for type in ("army", "buildings", "tech"):
            settings["manager"].setdefault(type, {"templates": []})

        self.army = self.Template(
            parent=self, master=self.nb_army, type="army", manager=manager
        )
        self.buildings = self.Template(
            parent=self, master=self.nb_buildings, type="buildings", manager=manager
        )
        self.tech = self.Template(
            parent=self, master=self.nb_tech, type="tech", manager=manager
        )

    def get_templates(self, settings: dict, template_type: str) -> None:
        if "server_world" not in settings:
            self.main_window.control_panel.show()
            custom_error(
                message="Najpierw wybierz serwer i numer świata",
                parent=self.main_window.control_panel.master,
            )
            return

        match template_type:
            case "army":
                self.get_army_templates(
                    driver=self.main_window.driver,
                    settings=self.settings,
                    widget=self.army.templates_groups,
                )

            case "buildings":
                self.get_buildings_templates(
                    driver=self.main_window.driver,
                    settings=self.settings,
                    widget=self.buildings.templates_groups,
                )

            case "tech":
                self.get_tech_templates(
                    driver=self.main_window.driver,
                    settings=self.settings,
                    widget=self.tech.templates_groups,
                )

        return

    def height_fix(self) -> None:
        if (self.master.winfo_height() - self.winfo_reqheight()) > 0:
            self.content_place(rely=0.0, relheight=1.0, relwidth=1.0)

    def get_template_url(
        self, driver: webdriver.Chrome, settings: dict, am_value: str
    ) -> str:
        base_url = app_functions.base_url(settings)
        village_id = game_data(driver, "village.id")
        return base_url + f"village={village_id}&screen=am_{am_value}&mode=template"

    @app_functions.account_access
    def get_army_templates(
        self, driver: webdriver.Chrome, settings: dict, widget: ttk.Combobox = None
    ) -> bool:
        driver.get(self.get_template_url(driver, settings, "troops"))
        templates = [
            template.text
            for template in driver.find_elements(
                By.XPATH,
                "//*[@id='content_value']/form/div[2]/table/tbody/tr/td[1]/span",
            )
        ]

        widget["values"] = templates
        self.army.templates.clear()
        self.army.templates.extend(templates)

        return True

    @app_functions.account_access
    def get_buildings_templates(
        self, driver: webdriver.Chrome, settings: dict, widget: ttk.Combobox
    ) -> bool:
        driver.get(self.get_template_url(driver, settings, "village"))
        templates = [
            template.text
            for template in driver.find_elements(
                By.XPATH,
                "//*[@id='content_value']/div[3]/table/tbody/tr[position()>1]/td[1]/a[1]",
            )
        ]
        widget["values"] = templates

        return True

    @app_functions.account_access
    def get_tech_templates(
        self, driver: webdriver.Chrome, settings: dict, widget: ttk.Combobox
    ) -> bool:
        driver.get(self.get_template_url(driver, settings, "research"))
        templates = [
            template.text
            for template in driver.find_elements(
                By.XPATH,
                "//*[@id='content_value']/div[3]/table/tbody/tr[position()>1]/td[1]/a[1]",
            )
        ]
        widget["values"] = templates

        return True

    class Template:
        def __init__(
            self, parent: "Manager", master: ttk.Frame, type: str, manager: dict
        ) -> None:

            master.columnconfigure((0, 1), weight=1)

            self.main_window = parent.main_window
            settings = parent.settings

            self.templates: list = settings["manager"][type]["templates"]
            self.groups: list = settings["groups"]

            manager[type] = {}
            manager[type]["active"] = ttk.BooleanVar()

            ttk.Checkbutton(
                master,
                text=translate("Activate templates refresher"),
                variable=manager[type]["active"],
                onvalue=True,
                offvalue=False,
            ).grid(row=0, column=0, columnspan=3, padx=5, pady=20)
            ttk.Separator(master, orient=ttk.HORIZONTAL).grid(
                row=1, column=0, columnspan=3, sticky=ttk.EW
            )

            ttk.Label(master, text=translate("Currently available templates")).grid(
                row=2, column=0, padx=15, pady=20, sticky=ttk.W
            )
            self.templates_groups = ttk.Combobox(
                master, state="readonly", justify="center", values=self.templates
            )
            self.templates_groups.grid(row=2, column=1, pady=20)
            self.templates_groups.set(translate("Available templates"))

            ttk.Button(
                master,
                image=self.main_window.images.refresh,
                bootstyle="primary.Link.TButton",
                command=lambda: threading.Thread(
                    target=lambda: parent.get_templates(settings, type),
                    name="checking_groups",
                    daemon=True,
                ).start(),
            ).grid(row=2, column=2, padx=15, pady=20, sticky=ttk.E)

            # ttk.Label(
            #     master,
            #     text=translate(f"Match groups of villages with {type} templates"),
            # ).grid(row=3, column=0, columnspan=3, padx=10, pady=10)

            self.row = 4

            self.add = Label(
                master,
                image=self.main_window.images.add,
                image_on_hover=self.main_window.images.add_hover,
                command=lambda: self.add_template_group_pair(master=master),
            )
            self.add.grid(row=100, column=0, columnspan=3, pady=(30, 40), sticky=ttk.N)

        class TemplateGroupPair:
            def __init__(self, master: ttk.Frame, parent: "Manager.Template") -> None:
                self.groups = ttk.Combobox(
                    master, values=parent.groups, state="readonly", justify=ttk.CENTER
                )
                self.groups.grid(
                    row=parent.row,
                    column=0,
                    padx=15,
                    pady=10,
                    sticky=ttk.W,
                )
                self.groups.set(translate("Choose group"))

                def templates_update() -> None:
                    self.templates["values"] = parent.templates

                self.templates = ttk.Combobox(
                    master,
                    values=parent.templates,
                    state="readonly",
                    postcommand=templates_update,
                    justify=ttk.CENTER,
                )
                self.templates.grid(row=parent.row, column=1, pady=10)
                self.templates.set(translate("Choose template"))

                ttk.Button(
                    master,
                    image=parent.main_window.images.exit,
                    style="danger.primary.Link.TButton",
                    padding=(10, 0)
                    # command=partial(
                    #     delete_template, index + 20, fake_templates, template_name
                    # ),
                ).grid(row=parent.row, column=2, padx=15, pady=10, sticky=ttk.NS)

        def add_template_group_pair(self, master: ttk.Frame) -> None:
            self.TemplateGroupPair(master=master, parent=self)
            self.row += 1
