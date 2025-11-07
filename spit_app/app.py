import json
from textual import on
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, TextArea
from spit_app.work import work_stream
import spit_app.message as message
import spit_app.utils as utils
from spit_app.config.config_app import ConfigScreen
from spit_app.config.config_settings import ConfigSettings

class SpitApp(App):
    NAME = "spit.py"
    VERSION = "0.1"
    AUTO_FOCUS = "#text-area"
    BINDINGS = [
            ("ctrl+enter", "submit", "Submit"),
            ("ctrl+escape", "abort", "Abort"),
            ("ctrl+s", "stop_follow", "Follow stream:[ON]"),
            ("ctrl+s", "follow", "Follow stream:[OFF]"),
            ("ctrl+m", "config_screen", "Config")
    ]
    CSS_PATH = './styles/main.tcss'

    def __init__(self):
        super().__init__()
        self.config = ConfigSettings()
        self.config.load()
        self.title_update()
        utils.load_state(self)
        self.follow = True
        self.work = None
        self.curr_children = 0

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

    async def action_submit(self) -> None:
        if self.text_area.text:
            self.state.append({"role": "user", "content": self.text_area.text})
            utils.write_chat_history(self)
            await message.mount(self, "request", "")
            await utils.render_message(self, self.text_area.text)
            self.text_area.text = ""
        self.curr_children = len(self.chat_view.children)
        self.work = self.run_worker(work_stream(self))

    def action_follow(self) -> None:
        self.follow = True
        self.refresh_bindings()

    def action_stop_follow(self) -> None:
        self.follow = False
        self.refresh_bindings()

    async def action_abort(self) -> None:
        self.work.cancel()
        utils.remove_last_roles_msgs(self, ["assistant", "tool"])
        await message.remove_last_children(self)
        utils.write_chat_history(self)
        self.refresh_bindings()

    async def action_config_screen(self) -> None:
        await self.push_screen(ConfigScreen())

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        running = False
        if self.work and self.work.is_running:
            running = True
        if action == "follow":
            if self.follow:
                return False
        if action == "stop_follow":
            if not self.follow:
                return False
        if action == "submit":
            active = self.config.config["active_config"]
            endpoint_url = self.config.config["configs"][active]["endpoint_url"]
            if not running and endpoint_url and self.text_area.text == "" and self.state[-1]["role"] == "user":
                return True
            if running or not endpoint_url or self.text_area.text == "":
                return False
        if action == "abort":
            if not running:
                return False
        return True

    @on(TextArea.Changed)
    def update_bindings(self) -> None:
        self.refresh_bindings()

    def on_worker_state_changed(self) -> None:
        self.refresh_bindings()
