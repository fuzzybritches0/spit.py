# SPDX-License-Identifier: GPL-2.0
from textual.containers import VerticalScroll
from .message.message import Message
from .work import Work

class ChatView(VerticalScroll):
    BINDINGS = [
        ("ctrl+enter", "continue", "Continue"),
        ("u", "undo", "Undo"),
        ("r", "redo", "Redo")
    ]

    def __init__(self, chat) -> None:
        super().__init__()
        self.anchor()
        self.chat = chat
        self.messages = self.chat.messages
        self.id = "chat-view"
        self.focused_message = None

    def focus_message(self, index: int, scroll_visible: bool = True) -> None:
        self.children[index].focus(scroll_visible=scroll_visible)
        self.focused_message = self.children[index]

    async def mount_message(self, message) -> None:
        await self.mount(Message(self.chat, message))
        await self.children[-1].process()
        await self.children[-1].finish()

    async def action_continue(self) -> None:
        if (self.messages[-1]["role"] == "user" or self.messages[-1] == "tool" or
            self.messages[-1]["role"] == "assistant" and "tool_calls" in
            self.messages[-1]):
            work = Work(self.chat)
            self.chat.work = self.run_worker(work.work_stream())

    async def action_undo(self) -> None:
        await self.chat.undo.undo()

    async def action_redo(self) -> None:
        await self.chat.undo.redo()

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "continue":
                if self.chat.is_working() or self.chat.text_area.is_edit or not self.messages:
                    return False
                if self.messages[-1]["role"] == "assistant":
                    if not "tool_calls" in self.messages[-1]:
                        return False
            case "undo":
                if self.chat.is_working() or self.chat.text_area.is_edit:
                    return False
                if self.chat.undo.undo_index == -1:
                    return False
            case "redo":
                if self.chat.is_working() or self.chat.text_area.is_edit:
                    return False
                if self.chat.undo.undo_index == len(self.chat.undo.undo_list)-1:
                    return False
                if len(self.chat.undo.undo_list) == 0:
                    return False
        return True
