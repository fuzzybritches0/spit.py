# SPDX-License-Identifier: GPL-2.0
from textual.app import ComposeResult
from textual.containers import Vertical
from .undo import Undo
from .chat_text_area import ChatTextArea
from .chat_settings import ChatSettings
from .chat_view import ChatView
from spit_app.modal_screens import InfoScreen

class Chat(Vertical):
    BINDINGS = [
        ("ctrl+escape", "abort", "Abort"),
        ("escape", "change_focus", "Focus"),
        ("ctrl+s", "settings", "Settings")
    ]

    def __init__(self, id: str) -> None:
        super().__init__()
        self.settings = self.app.settings
        self.classes = "chat"
        self.id = id
        content = self.app.read_json(f"chats/{self.id}.json")
        self.csettings = content["settings"]
        self.chat_ctime = content["ctime"]
        self.chat_desc = content["settings"]["desc"]["value"]
        self.chat_endpoint = content["settings"]["endpoint"]["value"]
        self.chat_model = content["settings"]["model"]["value"]
        self.chat_model_settings = content["settings"]["model_settings"]["value"]
        self.chat_prompt = content["settings"]["prompt"]["value"]
        self.chat_tools = content["settings"]["tools"]["value"]
        self.messages = content["messages"]
        self.model = content["model"]
        self.work = None
        self.chat_view = ChatView(self)
        self.text_area = ChatTextArea(self)
        self.undo = Undo(self)

    def is_working(self) -> bool:
        if self.work and self.work.is_running:
            return True
        return False

    def compose(self) -> ComposeResult:
        yield ChatSettings(self)
        yield self.chat_view
        yield self.text_area

    async def settings_exist(self) -> bool:
        if not self.chat_endpoint in self.settings.endpoints:
                await self.app.push_screen(InfoScreen("Endpoint settings not found! Did you remove them?"))
                return False
        if self.chat_prompt and not self.chat_prompt in self.settings.prompts:
                await self.app.push_screen(InfoScreen("System prompt not found! Did you remove it?"))
                return False
        return True

    def write_chat_history(self) -> bool:
        content = {}
        content["ctime"] = self.chat_ctime
        self.csettings["desc"]["value"] = self.chat_desc
        self.csettings["endpoint"]["value"] = self.chat_endpoint
        self.csettings["model"]["value"] = self.chat_model
        self.csettings["model_settings"]["value"] = self.chat_model_settings
        self.csettings["prompt"]["value"] = self.chat_prompt
        self.csettings["tools"]["value"] = self.chat_tools
        content["settings"] = self.csettings
        content["messages"] = self.messages
        content["model"] = self.model
        return self.app.write_json(f"chats/{self.id}.json", content)
    
    def action_change_focus(self) -> None:
        if self.app.focused.id.startswith("select-") and not self.text_area.was_focused:
            self.chat_view.focus()
        else:
            self.text_area.focus()

    async def action_abort(self) -> None:
        self.work.cancel()
        del self.messages[-1]
        await self.chat_view.children[-1].remove()
        self.refresh_bindings()

    def action_settings(self) -> None:
        self.query_one("#select-endpoint").action_show_overlay()

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        if action == "abort":
            return self.is_working()
        elif action == "settings":
            return not self.is_working()
        return True

    async def on_mount(self) -> None:
        self.settings.active_chat = self.id
        self.settings.save()
        self.app.focused_container = self
        if not self.messages:
            self.text_area.focus()
        else:
            self.chat_view.focus()

    def focus(self) -> None:
        self.settings.active_chat = self.id
        self.settings.save()
        self.app.query_one("#side-panel").can_focus = False
        if self.text_area.was_focused:
            self.text_area.focus()
        else:
            self.chat_view.focus()
