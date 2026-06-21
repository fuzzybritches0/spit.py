# SPDX-License-Identifier: GPL-2.0
import json
from textual.widgets import TextArea
from .work import Work
from .message.message import Message

class ChatTextArea(TextArea):
    BINDINGS = [
        ("ctrl+enter", "submit", "Submit"),
        ("ctrl+enter", "save_edit", "Save"),
        ("ctrl+escape", "cancel_edit", "Cancel")
    ]

    def __init__(self, chat):
        super().__init__()
        self.chat = chat
        self.chat_view = self.chat.chat_view
        self.messages = self.chat.messages
        self.id = "text-area"
        self.tab_behavior = "indent"
        self.temp = ""
        self.is_edit = False
        self.was_focused = False
        self.was_empty = True

    def action_cancel_edit(self):
        self.is_edit = False
        self.text = self.temp
        self.chat_view.focus()

    async def action_save_edit(self):
        index = self.chat_view.children.index(self.edit_container)
        self.chat.undo.append_undo("change", self.edit_container.message, index)
        if self.scontent == "tool_calls":
            self.edit_container.message[self.scontent][self.scontent_count] = json.loads(self.text)
        else:
            if type(self.edit_container.message[self.scontent]) is str:
                self.edit_container.message[self.scontent] = self.text
            else:
                self.edit_container.message[self.scontent][self.scontent_count]["text"] = self.text
        self.text = self.temp
        await self.edit_container.reset()
        await self.edit_container.finish()
        self.chat.write_chat_history()
        self.is_edit = False
        self.chat_view.focus()

    async def action_submit(self) -> None:
        if self.messages and self.messages[-1]["role"] == "user":
            self.chat.undo.append_undo("change", self.messages[-1], len(self.messages)-1)
            self.messages[-1]["content"].append({"type": "text", "text": self.text})
        else:
            self.messages.append({"role": "user", "content": [{"type": "text", "text": self.text}]})
            self.chat.undo.append_undo("insert", self.messages[-1], len(self.messages))
            await self.chat_view.mount(Message(self.chat, self.messages[-1]))
        self.chat.write_chat_history()
        self.chat_view.focus()
        await self.chat_view.children[-1].finish()
        await self.chat_view.children[-1].wait_for_refresh()
        self.chat_view.scroll_end(animate=False, immediate=True)
        self.text = ""
        work = Work(self.chat)
        self.chat.work = self.run_worker(work.work_stream())

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "save_edit":
                return self.is_edit
            case "cancel_edit":
                return self.is_edit
            case "submit":
                if self.chat.chat_model == "none":
                    return False
                if not "completion" in self.chat.model_capabilities:
                    return False
                if self.chat.is_working() or self.is_edit:
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
        self.app.query_one("#side-panel").can_focus = False
        self.was_focused = True
