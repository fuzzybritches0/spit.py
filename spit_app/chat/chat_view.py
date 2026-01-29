# SPDX-License-Identifier: GPL-2.0
from textual import events
from textual.containers import VerticalScroll
from .message.message import Message
from .work import Work
from spit_app.modal_screens import LoadingScreen

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

    async def callback(self, signal: int) -> None:
        if signal == 0:
            self.chat.write_chat_history()
            await self.children[-1].finish()
        elif signal == 1:
            await self.mount_message(True)
        elif signal == 2:
            await self.children[-1].process()

    def focus_message(self, index: int, scroll_visible: bool = True) -> None:
        self.children[index].focus(scroll_visible=scroll_visible)
        self.focused_message = self.children[index]

    async def mount_message(self, new: bool = False) -> None:
        await self.mount(Message(self.chat, self.messages[-1]))
        if not new:
            await self.children[-1].process()
            await self.children[-1].finish()

    async def action_continue(self) -> None:
        if (self.messages[-1]["role"] == "user" or self.messages[-1]["role"] == "tool" or
            (self.messages[-1]["role"] == "assistant" and "tool_calls" in self.messages[-1])):
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

    async def on_worker_state_changed(self) -> None:
        self.refresh_bindings()

    async def on_mount(self) -> None:
        if self.messages:
            loading_screen = LoadingScreen()
            await self.app.push_screen(loading_screen)
            for message in self.messages:
                await self.mount(Message(self.chat, message))
                await self.children[-1].process()
                await self.children[-1].finish()
            await loading_screen.dismiss()

    def on_focus(self) -> None:
        self.app.query_one("#side-panel").can_focus = False
        if not self.children:
            self.chat.text_area.focus()
        if self.focused_message:
            self.focused_message.focus()

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        if not event.control is self.chat.text_area:
            self.focused_message = event.control
