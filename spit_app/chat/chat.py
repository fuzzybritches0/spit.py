# SPDX-License-Identifier: GPL-2.0
import asyncio
from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from .undo import Undo
from .chat_text_area import ChatTextArea
from .chat_settings import ChatSettings
from .chat_view import ChatView
from .multimodal import load_image_base64, image_url
from spit_app.modal_screens import ChooseImageFile
from spit_app.chat.message.message import Message

class Chat(Vertical):
    BINDINGS = [
        ("ctrl+escape", "abort", "Abort"),
        ("escape", "change_focus", "Focus"),
        ("ctrl+s", "settings", "Settings"),
        ("ctrl+i", "add_image", "Add image")
    ]

    def __init__(self, id: str) -> None:
        super().__init__()
        self.settings = self.app.settings
        self.classes = "chat"
        self.id = id
        content = self.app.read_json(f"chats/{self.id}.json")
        self.ctime = content["ctime"]
        self.csettings = content["settings"]
        self.messages = content["messages"]
        self.model_capabilities = []
        self.work = None
        self.chat_view = ChatView(self)
        self.text_area = ChatTextArea(self)
        self.chat_settings = ChatSettings(self)
        self.undo = Undo(self)

    def cs(self, key: str, value: any = "_None_") -> str|None:
        if not value == "_None_":
            self.csettings[key]["value"] = value
        else:
            return self.csettings[key]["value"]

    def is_working(self) -> bool:
        if self.work and self.work.is_running:
            return True
        return False

    def compose(self) -> ComposeResult:
        yield self.chat_settings
        yield self.chat_view
        yield self.text_area

    def write_chat_history(self) -> bool:
        content = {}
        content["ctime"] = self.ctime
        content["settings"] = self.csettings
        content["messages"] = self.messages
        return self.app.write_json(f"chats/{self.id}.json", content)
    
    def action_change_focus(self) -> None:
        if not self.chat_view.has_focus_within:
            self.chat_view.focus()
        else:
            self.text_area.focus()

    async def action_abort(self) -> None:
        self.work.cancel()
        self.refresh_bindings()

    def action_settings(self) -> None:
        self.query_one("#select-endpoint").action_show_overlay()

    @work
    async def action_add_image(self) -> None:
        url = await self.app.push_screen_wait(ChooseImageFile())
        image = None
        if url:
            try:
                image = await asyncio.to_thread(load_image_base64, url)
            except Exception as exception:
                self.app.exception = exception
                return None
        if image:
            if self.messages and self.messages[-1]["role"] == "user":
                self.undo.append_undo("change", self.messages[-1])
                self.messages[-1]["content"].append(image_url(image))
            else:
                self.messages.append({"role": "user", "content": [image_url(image)]})
                self.undo.append_undo("insert", self.messages[-1])
                await self.chat_view.mount(Message(self, self.messages[-1]))
            self.write_chat_history()
            await self.chat_view.children[-1].finish()
            self.chat_view.focus()
            self.chat_view.scroll_end(animate=False)

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        if action == "abort":
            return self.is_working()
        elif action == "settings":
            return not self.is_working()
        elif action == "add_image":
            if not "multimodal" in self.model_capabilities or self.is_working() or self.text_area.is_edit:
                return False
        return True

    async def on_mount(self) -> None:
        self.settings.active_chat = self.id
        self.settings.save()

    def focus(self) -> None:
        self.settings.active_chat = self.id
        self.settings.save()
        self.app.query_one("#side-panel").can_focus = False
        if self.text_area.was_focused:
            self.text_area.focus()
        else:
            self.chat_view.focus()
