# SPDX-License-Identifier: GPL-2.0
from textual.containers import VerticalScroll
from .textual_message import RemoveMessage
from .message.message import Message
from ..modal_screens import LoadingScreen
from .work import Work
from .callback import CallbackMixIn

class ChatView(VerticalScroll, CallbackMixIn):
    BLANK = True
    BINDINGS = [
        ("ctrl+enter", "continue", "Continue"),
        ("ctrl+e", "edit_on", "Edit On"),
        ("ctrl+e", "edit_off", "Edit Off"),
        ("u", "undo", "Undo"),
        ("r", "redo", "Redo")
    ]

    def __init__(self, chat) -> None:
        super().__init__()
        self.anchor()
        self.chat = chat
        self.cs = chat.cs
        self.messages = self.chat.messages
        self.focused_message = None
        self.is_edit = False
        self.id = "chat-view"

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
        self.show_cots(False)
        self.chat.text_area.display = True
        self.is_edit = False
        self.refresh_bindings()

    async def action_undo(self) -> None:
        await self.chat.undo.undo()

    async def action_redo(self) -> None:
        await self.chat.undo.redo()

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
                if not "tool_calls" in self.messages[-1]:
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
        return True

    async def on_remove_message(self, message: RemoveMessage) -> None:
        self.chat.undo.append_undo("remove", self.messages[message.index], message.index)
        await self.children[message.index].remove()
        del self.messages[message.index]
        self.chat.write_chat_history()
        if self.messages:
            self.children[message.index-1].focus(scroll_visible=False)
        if not self.children:
            self.chat.text_area.focus()

    def on_focus(self) -> None:
        self.app.query_one("#side-panel").can_focus = False
        self.chat.text_area.was_focused = False
        if self.focused_message:
            self.focused_message.focus(scroll_visible=False)
        else:
            if self.children:
                self.children[-1].focus(scroll_visible=False)
            elif not self.chat.undo.undo_list:
                self.chat.text_area.focus()

    async def load(self) -> None:
        if self.messages:
            loading_screen = LoadingScreen()
            await self.app.push_screen(loading_screen)
            async with self.batch():
                for message in self.messages:
                    await self.mount(Message(self.chat, message))
                    await self.children[-1].finish()
            loading_screen.dismiss()
            self.children[-1].focus(scroll_visible=False)
        else:
            self.chat.text_area.focus()
