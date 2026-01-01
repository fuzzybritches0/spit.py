# SPDX-License-Identifier: GPL-2.0
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer
from spit_app.settings import Settings
from spit_app.actions import ActionsMixIn
from spit_app.actions import bindings
from spit_app.handlers import HandlersMixIn
from spit_app.tool_call import ToolCall
from spit_app.side_panel.side_panel import SidePanel

class SpitApp(ActionsMixIn, HandlersMixIn, App):
    NAME = "spit.py"
    VERSION = "0.1"
    TITLE = f"{NAME} v{VERSION}"
    COPYRIGHT = "github.com/fuzzybritches0"
    LICENSE = "GPL-2.0"
    CSS_PATH = './styles/app.css'
    BINDINGS = bindings

    def __init__(self):
        super().__init__()
        #self.applog("LOG START:")
        self.settings = Settings(self)
        self.settings.load()
        self.tool_call = ToolCall(self)
        self.watch(self.app, "theme", self.on_theme_changed, init=False)

    def applog(self, text: str) -> None:
        with open("./log.txt", "a") as file:
            file.write(repr(text) + "\n")

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="app"):
            yield SidePanel()
            yield Vertical(id="main")
        yield Footer()

    def focus_first(self, index: int) -> None:
        child = self.query_one("#main").children[index]
        if child.id.startswith("chat-"):
            child.children[0].focus()
        elif child.children[0].id == "option-list":
            child.children[0].focus()
        else:
            child.children[1].focus()
