# SPDX-License-Identifier: GPL-2.0
from textual.widgets import TextArea
from .work import Work

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
        self.was_empty = True

    def action_cancel_edit(self):
        self.chat.edit = False
        self.text = self.temp

    async def action_submit(self) -> None:
        if (self.text and
            (not self.messages or self.messages[-1]["role"] == "assistant")):
            self.chat.save_message({"role": "user", "content": self.text})
            await self.chat_view.mount_message(self.messages[-1])
            self.chat_view.scroll_end(animate=False)
            self.text = ""
            work = Work(self.chat)
            self.chat.work = self.run_worker(work.work_stream())

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "save_edit":
                return self.chat.edit
            case "cancel_edit":
                return self.chat.edit
            case "submit":
                if self.chat.is_working() or self.chat.edit:
                    return False
                if not self.text:
                    return False
                if self.messages and (self.messages[-1]["role"] == "user" or
                    self.messages[-1]["role"] == "tool"):
                    return False
        return True

    def on_text_area_changed(self) -> None:
        if self.text:
            if self.was_empty:
                self.refresh_bindings()
                self.was_empty = False
        else:
            if not self.was_empty:
                self.refresh_bindings()
                self.was_empty = True
