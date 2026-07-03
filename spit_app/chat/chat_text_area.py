# SPDX-License-Identifier: GPL-2.0
import json
from textual.widgets import TextArea
from .work import Work
from .message.message import Message

class ChatTextArea(TextArea):
    BINDINGS = [
        ("ctrl+enter", "submit", "Submit")
    ]

    def __init__(self, chat):
        super().__init__()
        self.chat = chat
        self.cs = chat.cs
        self.chat_view = chat.chat_view
        self.messages = chat.messages
        self.id = "text-area"
        self.tab_behavior = "indent"
        self.was_focused = False
        self.was_empty = True

    async def action_submit(self) -> None:
        if self.messages and self.messages[-1]["role"] == "user":
            self.chat.undo.append_undo("change", self.messages[-1], len(self.messages)-1)
            self.messages[-1]["content"].append({"type": "text", "text": self.text})
        else:
            self.messages.append({"role": "user", "content": [{"type": "text", "text": self.text}]})
            self.chat.undo.append_undo("insert", self.messages[-1], len(self.messages)-1)
            await self.chat_view.mount(Message(self.chat, self.messages[-1]))
        self.chat.write_chat_history()
        await self.chat_view.children[-1].finish()
        await self.chat_view.children[-1].wait_for_refresh()
        self.chat_view.children[-1].focus(scroll_visible=False)
        self.chat_view.scroll_end(animate=False, immediate=True)
        self.text = ""
        self.chat._work = Work(self.chat)
        self.chat.work = self.run_worker(self.chat._work.work_stream())

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "submit":
            if self.cs("model") == "none":
                return False
            if not "completion" in self.chat.model_capabilities:
                return False
            if self.chat.is_working() or self.chat_view.is_edit:
                return False
            if not self.text:
                return False
        return True

    async def on_worker_state_changed(self) -> None:
        self.refresh_bindings()

    def on_text_area_changed(self) -> None:
        if self.text:
            if self.was_empty:
                self.refresh_bindings()
                self.was_empty = False
        else:
            if not self.was_empty:
                self.refresh_bindings()
                self.was_empty = True

    def on_focus(self) -> None:
        self.was_focused = True
