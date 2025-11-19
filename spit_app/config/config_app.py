# SPDX-License-Identifier: GPL-2.0
from textual import on
from textual.widgets import Button, Header, Footer, OptionList
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container
from spit_app.config.settings import get_settings
import spit_app.config.config_screens as cs

class ConfigApp(ModalScreen):
    CSS_PATH = "../styles/config.css"

    def __init__(self) -> None:
        super().__init__()
        self.title = f"{self.app.NAME} v{self.app.VERSION} - Configuration"
        self.config = self.app.config
        self.settings = get_settings(self)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(id="Main")
        yield Footer()

    async def on_mount(self) -> None:
        self.main_container = self.query_one("#Main")
        self.dyn_container = Container()
        await self.main_container.mount(self.dyn_container)
        await cs.select_config_screen(self)

    def valid_values(self) -> bool:
        for setting, stype, desc, defvalue, *validators in self.settings:
            if not self.query_one(f"#{setting}").is_valid:
                return False
        return True

    def store_values(self) -> None:
        for setting, stype, desc, defvalue, *validators in self.settings:
            newvalue = self.query_one(f"#{setting}").value
            self.config.store(self.cconfig, setting, stype, newvalue)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "delete":
            self.config.delete_config(self.cconfig)
            self.app.title_update()
            self.dismiss()
        elif event.button.id == "set_active":
            if self.valid_values():
                self.store_values()
                self.config.save()
            self.config.set_active(self.cconfig)
            self.app.title_update()
            self.dismiss()
        elif event.button.id == "save":
            if self.valid_values():
                self.store_values()
                self.config.save()
                self.app.title_update()
                self.dismiss()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "select_new_config":
            self.cconfig = self.config.new()
            await cs.clean_dyn_container(self)
            await cs.edit_settings_screen(self)
        else:
            self.cconfig = int(event.option.id[14:])
            await cs.clean_dyn_container(self)
            await cs.edit_settings_screen(self)
