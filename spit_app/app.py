import json
from textual import events
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, TextArea
from spit_app.work import work_stream
import spit_app.message as message
import spit_app.utils as utils
from spit_app.config.config_app import ConfigScreen
from spit_app.config.config_settings import ConfigSettings

class Debug():
    def log(app, text: str) -> None:
        with open("./log.txt", "a") as file:
            file.write(repr(text) + "\n")

class SpitApp(App):
    NAME = "spit.py"
    VERSION = "0.1"
    AUTO_FOCUS = "#text-area"
    BINDINGS = [
            ("escape", "change_focus", "Focus"),
            ("ctrl+enter", "submit", "Submit"),
            ("ctrl+escape", "abort", "Abort"),
            ("ctrl+m", "config_screen", "Config"),
            ("ctrl+r", "remove_last_turn", "Remove last turn")
    ]
    CSS_PATH = './styles/main.css'

    def __init__(self):
        super().__init__()
        #self.logger = Debug()
        #self.logger.log("LOG START:")
        self.config = ConfigSettings()
        self.config.load()
        self.title_update()
        utils.load_state(self)
        self.work = None
        self.focused_message = None

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

    async def on_mount(self) -> None:
        await utils.render_messages(self)

    def action_change_focus(self) -> None:
            self.text_area.focus()

    async def action_submit(self) -> None:
        if self.text_area.text:
            if self.state[-1]["role"] == "user":
                self.state[-1]["content"]+="\n\n"+self.text_area.text.strip("\n ")
            else:
                self.state.append({"role": "user", "content": self.text_area.text})
            utils.write_chat_history(self)
            await utils.render_message(self, "request", self.text_area.text)
            self.text_area.text = ""
        if self.text_area.text or self.state[-1]["role"] == "user":
            self.work = self.run_worker(work_stream(self))

    async def action_abort(self) -> None:
        self.work.cancel()
        utils.remove_last_roles_msgs(self, ["assistant", "tool"])
        await message.remove_last_turn(self)
        utils.write_chat_history(self)
        self.refresh_bindings()

    async def action_remove_last_turn(self) -> None:
        if self.state[-1]["role"] == "user":
            utils.remove_last_roles_msgs(self, ["user"])
        else:
            utils.remove_last_roles_msgs(self, ["assistant", "tool"])
        await message.remove_last_turn(self)
        utils.write_chat_history(self)
        self.refresh_bindings()

    async def action_config_screen(self) -> None:
        await self.push_screen(ConfigScreen())

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        running = False
        if self.work and self.work.is_running:
            running = True
        if action == "submit":
            active = self.config.config["active_config"]
            endpoint_url = self.config.config["configs"][active]["endpoint_url"]
            if running or not endpoint_url:
                return False
        if action == "abort":
            if not running:
                return False
        if action == "remove_last_turn":
            if running or not self.state or len(self.state) == 1 and self.state[0]["role"] == "system":
                return False
        return True

    def on_worker_state_changed(self) -> None:
        self.refresh_bindings()

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        if self.chat_view.has_focus:
            if self.focused_message:
                self.focused_message.focus()
        if not self.chat_view.has_focus and not self.text_area.has_focus:
            if event.control.parent.id == "chat-view":
                self.focused_message = event.control
