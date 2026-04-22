# SPDX-License-Identifier: GPL-2.0
import json
from textual.reactive import var
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer
from spit_app.settings import Settings
from spit_app.actions import ActionsMixIn
from spit_app.actions import bindings
from spit_app.handlers import HandlersMixIn
from spit_app.tool_call import ToolCall
from spit_app.side_panel import SidePanel
from spit_app.modal_screens import ErrorScreen

class SpitApp(ActionsMixIn, HandlersMixIn, App):
    NAME = "spit.py"
    VERSION = "0.1"
    TITLE = f"{NAME} v{VERSION}"
    COPYRIGHT = "github.com/fuzzybritches0"
    LICENSE = "GPL-2.0"
    CSS_PATH = './styles.css'
    BINDINGS = bindings
    exception = var(None, always_update=True, init=False)

    def __init__(self):
        super().__init__()
        #self.applog("LOG START:")
        self.settings = Settings(self)
        self.path = self.settings.path
        self.settings.load()
        self.tool_call = ToolCall(self)
        self.focused_container = None
        self.confirm_exit = False
        self.watch(self.app, "theme", self.on_theme_changed, init=False)

    async def watch_exception(self, exception: Exception) -> None:
        await self.push_screen(ErrorScreen(exception))

    def applog(self, text: str) -> None:
        with open("./log.txt", "a") as file:
            file.write(repr(text) + "\n")

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="app"):
            yield SidePanel()
            yield Vertical(id="main")
        yield Footer()

    async def maybe_reload(self, id: str) -> None:
        try:
            loaded = self.query_one("#main").query_one(f"#{id}")
        except:
            loaded = None
        if loaded:
            if loaded.children[0].id == "option-list":
                await loaded.remove_children()
                await loaded.select_main_screen()
            else:
                await loaded.remove_children()
                loaded.load(loaded.uuid)
                await loaded.edit_manage_screen()

    def write_json(self, path, content) -> bool:
        path = path.split("/")
        if len(path) > 1:
            file = self.path[path[0]] / path[1]
        else:
            file = self.path[path[0]]
        jcont = json.dumps(content)
        try:
            file.write_text(jcont)
        except Exception as exception:
            if type(exception).__name__ in ("OSError", "PermissionError"):
                self.exception = exception
            else:
                raise exception
            return False
        return True

    def read_json(self, path) -> None|dict:
        path = path.split("/")
        if len(path) > 1:
            file = self.path[path[0]] / path[1]
        else:
            file = self.path[path[0]]
        try:
            text = file.read_text()
        except Exception as exception:
            if type(exception).__name__ in ("OSError", "PermissionError"):
                self.exception = exception
                return None
            else:
                raise exception
        return json.loads(text)
