# SPDX-License-Identifier: GPL-2.0
from textual.events import Focus
from textual.containers import VerticalScroll
from .textual_message import RemoveMessage
from .message.message import Message
from ..modal_screens import LoadingScreen
from .work import Work

bindings = [
    ("ctrl+up", "previous_message", "Prev."),
    ("ctrl+down", "next_message", "Next"),
    ("ctrl+enter", "continue", "Cont."),
    ("u", "undo", "Undo"),
    ("r", "redo", "Redo"),
    ("a", "add", "+Msg."),
    ("ctrl+e", "edit_on", "Edit On"),
    ("ctrl+e", "edit_off", "Edit Off")
]

class ChatViewActionsMixIn:
    def show_cots(self, show: bool = True) -> None:
        for message in self.children:
            if "reasoning" in message.pr:
                message.pr["reasoning"].display = show

    async def reset_message_edit(self) -> None:
        async with self.batch():
            for child in self.children:
                if child.is_edit:
                    await child.reset()
                    await child.finish()

    async def action_continue(self) -> None:
        if (self.messages[-1]["role"] == "user" or self.messages[-1]["role"] == "tool" or
            (self.messages[-1]["role"] == "assistant" and "tool_calls" in self.messages[-1])):
            self.chat._work = Work(self.chat)
            self.scroll_end(animate=False, immediate=True)
            self.chat.work = self.run_worker(self.chat._work.work_stream())

    def action_edit_on(self) -> None:
        self.show_cots(True)
        self.chat.text_area.display = False
        self.is_edit = True
        self.refresh_bindings()

    async def action_edit_off(self) -> None:
        await self.reset_message_edit()
        if self.focused_message and "reasoning" in self.focused_message.pr:
            if self.focused_widget is self.focused_message.pr["reasoning"].children[0]:
                self.focused_message.focus()
        self.show_cots(False)
        self.chat.text_area.display = True
        self.is_edit = False
        self.refresh_bindings()

    def action_previous_message(self) -> None:
        index = self.chat.message_index(self.focused_message.message) - 1
        if index >= 0:
            self.children[index].focus()

    def action_next_message(self) -> None:
        index = self.chat.message_index(self.focused_message.message) + 1
        last_index = len(self.messages) - 1
        if index <= last_index:
            self.children[index].focus()

    async def action_undo(self) -> None:
        await self.chat.undo.undo()

    async def action_redo(self) -> None:
        await self.chat.undo.redo()

    async def action_add(self) -> None:
        self.messages.append({"role": "user", "content": []})
        self.chat.undo.append_undo("insert", self.messages[0], 0)
        await self.mount(Message(self.chat, self.messages[0]))
        await self.children[0].status.update("")
        self.chat.write_chat_history()
        self.children[0].focus()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.chat.is_working():
            return False
        if action == "continue":
            if self.is_edit:
                return False
            if self.cs("model") == "none" or not self.messages:
                return False
            if not "completion" in self.chat.model_capabilities:
                return False
            if self.messages[-1]["role"] == "assistant":
                if "tool_calls" in self.messages[-1]:
                    return True
                return False
            if ((not "content" in self.messages[-1] or not self.messages[-1]["content"] or
                 not self.messages[-1]["content"][0]["text"]) and
                 (not "tools" in self.messages[-1] or not self.messages[-1]["tools"])):
                return False
        elif action ==  "undo":
            if self.chat.undo.undo_index == -1:
                return False
        elif action ==  "redo":
            if self.chat.undo.undo_index == len(self.chat.undo.undo_list)-1:
                return False
            if len(self.chat.undo.undo_list) == 0:
                return False
        elif action == "edit_on":
            if self.is_edit:
                return False
        elif action == "edit_off":
            if not self.is_edit:
                return False
        elif action == "add":
            if not self.is_edit or self.messages:
                return False
        return True
