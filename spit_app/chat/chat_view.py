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
        self.id = "chat-view"

    async def action_continue(self) -> None:
        if (self.messages[-1]["role"] == "user" or self.messages[-1]["role"] == "tool" or
            (self.messages[-1]["role"] == "assistant" and "tool_calls" in self.messages[-1])):
            work = Work(self.chat)
            self.scroll_end(animate=False, immediate=True)
            self.chat.work = self.run_worker(work.work_stream())

    async def action_undo(self) -> None:
        await self.chat.undo.undo()

    async def action_redo(self) -> None:
        await self.chat.undo.redo()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        match action:
            if self.chat.is_working() or self.chat.text_area.is_edit:
                return False
            case "continue":
                if self.cs("model") == "none" or not self.messages:
                    return False
                if not "completion" in self.chat.model_capabilities:
                    return False
                if self.messages[-1]["role"] == "assistant":
                    if not "tool_calls" in self.messages[-1]:
                        return False
            case "undo":
                if self.chat.undo.undo_index == -1:
                    return False
            case "redo":
                if self.chat.undo.undo_index == len(self.chat.undo.undo_list)-1:
                    return False
                if len(self.chat.undo.undo_list) == 0:
                    return False
        return True

    async def on_remove_message(self, message: RemoveMessage) -> None:
        self.chat.undo.append_undo("remove", self.messages[message.index], message.index)
        await self.children[message.index].remove()
        del self.messages[message.index]
        self.chat.write_chat_history()
        if not self.children:
            self.chat.text_area.focus()

    async def on_worker_state_changed(self) -> None:
        self.refresh_bindings()

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
