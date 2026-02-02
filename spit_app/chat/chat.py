# SPDX-License-Identifier: GPL-2.0
from textual.app import ComposeResult
from textual.containers import Vertical
from .undo import Undo
from .chat_text_area import ChatTextArea
from .chat_view import ChatView

class Chat(Vertical):
    BINDINGS = [
        ("ctrl+escape", "abort", "Abort"),
        ("escape", "change_focus", "Focus")
    ]

    def __init__(self, id: str) -> None:
        super().__init__()
        self.settings = self.app.settings
        self.classes = "chat"
        self.id = id
        content = self.app.read_json(f"chats/{self.id}.json")
        self.chat_ctime = content["ctime"]
        self.chat_desc = content["desc"]
        self.chat_endpoint = content["endpoint"]
        self.chat_prompt = content["prompt"]
        self.messages = content["messages"]
        self.work = None
        self.chat_view = ChatView(self)
        self.text_area = ChatTextArea(self)
        self.undo = Undo(self)

    def is_working(self) -> bool:
        if self.work and self.work.is_running:
            return True
        return False

    def compose(self) -> ComposeResult:
        yield self.chat_view
        yield self.text_area

    def write_chat_history(self) -> bool:
        content = {}
        content["ctime"] = self.chat_ctime
        content["desc"] = self.chat_desc
        content["endpoint"] = self.chat_endpoint
        content["prompt"] = self.chat_prompt
        content["messages"] = self.messages
        return self.app.write_json(f"chats/{self.id}.json", content)
    
    def save_message(self, umessage: dict) -> None:
        self.messages.append(umessage)
        self.undo.append_undo("append", umessage)
        self.write_chat_history()

    def action_change_focus(self) -> None:
        self.text_area.focus()

    async def action_abort(self) -> None:
        self.work.cancel()
        del self.messages[-1]
        await self.chat_view.children[-1].remove()
        self.refresh_bindings()

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "abort":
                return self.is_working()
        return True

    async def on_mount(self) -> None:
        if not self.messages:
            self.text_area.focus()
        else:
            self.chat_view.focus()

    def focus(self) -> None:
        self.app.query_one("#side-panel").can_focus = False
        self.chat_view.focus()
