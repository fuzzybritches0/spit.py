# SPDX-License-Identifier: GPL-2.0
from textual.widgets import Header, Footer
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container
from spit_app.settings.endpoint import EndpointMixIn
from spit_app.settings.endpoint_screens import EndpointScreensMixIn

class SettingsMixIn(ModalScreen):
    def __init__(self) -> None:
        super().__init__()
        self.title = f"{self.app.NAME} v{self.app.VERSION} - {self.MODULE} settings"
        self.settings = self.app.settings
        self.init()

    def compose(self) -> ComposeResult:
        yield Header()
        self.main_container = Container()
        yield self.main_container
        yield Footer()

    async def on_mount(self) -> None:
        self.dyn_container = Container()
        await self.main_container.mount(self.dyn_container)
        await self.select_endpoints_screen()

    async def clean_dyn_container(self) -> None:
        await self.dyn_container.remove_children()

class EndpointSettings(EndpointMixIn, EndpointScreensMixIn, SettingsMixIn):
    MODULE = "Endpoint"
    CSS_PATH = "../styles/endpoint.css"
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("ctrl+s", "set_active", "Set active"),
        ("escape", "dismiss", "Cancel")
    ]
