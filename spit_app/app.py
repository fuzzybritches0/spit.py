# SPDX-License-Identifier: GPL-2.0
import json
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer
from spit_app.settings import Settings
from spit_app.actions import ActionsMixIn
from spit_app.actions import bindings
from spit_app.handlers import HandlersMixIn
from spit_app.tool_call import ToolCall
from spit_app.side_panel import SidePanel

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
        self.path = self.settings.path
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

    async def maybe_remove(self, id: str) -> None:
        try:
            await self.query_one("#main").query_one(f"#{id}").remove()
        except:
            pass

    def write_json(self, path, content) -> bool:
        path = path.split("/")
        if len(path) > 1:
            file = self.path[path[0]] / path[1]
        else:
            file = self.path[path[0]]
        try:
            file.write_text(json.dumps(content))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            return False
        return True

    def read_json(self, path) -> None|dict:
        path = path.split("/")
        if len(path) > 1:
            file = self.path[path[0]] / path[1]
        else:
            file = self.path[path[0]]
        try:
            ret = json.loads(file.read_text())
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            return None
        return ret
