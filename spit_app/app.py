import json
from textual import work
from textual import on
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Container
from textual.widgets import Footer, Header, TextArea
from spit_app.work import Work
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
        self.streaming = False

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
        self.state.append({"role": "user", "content": self.text_area.text})
        utils.write_chat_history(self)
        await message.mount(self, "request", "")
        await utils.render_message(self, self.text_area.text)
        self.text_area.text = ""
        self.work_stream()

    @work(exclusive=True)
    async def work_stream(self) -> None:
        work = Work(self)
        await work.stream_response()
        while work.tool_calls:
            for tool_call in json.loads(work.tool_calls):
                self.state.append({"role": "tool",
                                  "tool_call_id": tool_call["id"],
                                  "name": tool_call["function"]["name"],
                                  "content": '{"unit":"celsius","temperature":12}'
                                   })
            work = Work(self)
            await work.stream_response()

    def action_follow(self) -> None:
        self.follow = True
        self.refresh_bindings()

    def action_stop_follow(self) -> None:
        self.follow = False
        self.refresh_bindings()

    def action_abort(self) -> None:
        self.streaming = False

    async def action_config_screen(self) -> None:
        await self.push_screen(ConfigScreen())

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "follow":
            if self.follow:
                return False
        if action == "stop_follow":
            if not self.follow:
                return False
        if action == "submit":
            active = self.config.config["active_config"]
            endpoint_url = self.config.config["configs"][active]["endpoint_url"]
            if self.streaming or not endpoint_url or self.text_area.text == "":
                return False
        if action == "abort":
            if not self.streaming:
                return False
        return True

    @on(TextArea.Changed)
    def update_bindings(self) -> None:
        self.refresh_bindings()
