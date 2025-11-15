# SPDX-License-Identifier: GPL-2.0
import json
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, TextArea
import spit_app.message as message
import spit_app.utils as utils
from spit_app.config.config_settings import ConfigSettings
from spit_app.actions.actions import ActionsMixIn
from spit_app.actions.actions import bindings
from spit_app.handlers.handlers import HandlersMixIn

class SpitApp(HandlersMixIn, ActionsMixIn, App):
    NAME = "spit.py"
    VERSION = "0.1"
    AUTO_FOCUS = "#text-area"
    CSS_PATH = './styles/main.css'
    BINDINGS = bindings

    def __init__(self):
        super().__init__()
        #self.applog("LOG START:")
        self.config = ConfigSettings()
        self.config.load()
        self.title_update()
        utils.load_state(self)
        self.work = None
        self.edit = False
        self.focused_message = None
        self.text_area_was_empty = True

    def applog(self, text: str) -> None:
        with open("./log.txt", "a") as file:
            file.write(repr(text) + "\n")

    def title_update(self) -> None:
        active = self.config.config["active_config"]
        name = self.config.config["configs"][active]["name"]
        self.title = f"{self.NAME} v{self.VERSION} - Chat - {name}"

    def compose(self) -> ComposeResult:
        yield Header()
        self.chat_view = VerticalScroll(id="chat-view")
        yield self.chat_view
        self.text_area = TextArea(id="text-area", tab_behavior="indent")
        yield self.text_area
        yield Footer()
