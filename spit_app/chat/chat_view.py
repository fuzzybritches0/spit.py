# SPDX-License-Identifier: GPL-2.0
import asyncio
from textual import work
from textual.containers import VerticalScroll
from .message.message import Message
from .work import Work

class ChatView(VerticalScroll):
    BLANK = True
    BINDINGS = [
        ("ctrl+enter", "continue", "Continue"),
        ("u", "undo", "Undo"),
        ("r", "redo", "Redo")
    ]

    def __init__(self, chat) -> None:
        super().__init__()
        self.working = False
        self.anchor()
        self.anchor_visual()
        self.chat = chat
        self.messages = self.chat.messages
        self.focused_message = None
        self.id = "chat-view"

    async def callback(self, signal: int) -> None:
        if signal == 0:
            self.chat.write_chat_history()
            self.chat.undo.append_undo("append", self.chat.messages[-1], len(self.messages))
            await self.children[-1].finish()
        elif signal == 1:
            await self.mount(Message(self.chat, self.messages[-1]))
            self.children[-1].focus(scroll_visible=False)
            self.scroll_end(animate=False, immediate=True)
        elif signal == 2:
            await self.children[-1].process()

    async def action_continue(self) -> None:
        if (self.messages[-1]["role"] == "user" or self.messages[-1]["role"] == "tool" or
            (self.messages[-1]["role"] == "assistant" and "tool_calls" in self.messages[-1])):
            work = Work(self.chat)
            self.chat.work = self.run_worker(work.work_stream())

    async def action_undo(self) -> None:
        await self.chat.undo.undo()

    async def action_redo(self) -> None:
        await self.chat.undo.redo()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "continue":
                if self.chat.chat_model == "none":
                    return False
                if not "completion" in self.chat.model_capabilities:
                    return False
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

    def on_focus(self) -> None:
        self.app.query_one("#side-panel").can_focus = False
        self.chat.text_area.was_focused = False
        if self.focused_message:
            self.focused_message.focus()
        else:
            if self.children:
                self.children[-1].focus(scroll_visible=False)

    @work
    async def load(self) -> None:
        if self.messages:
            self.working = True
            await self.mount(Message(self.chat, self.messages[-1]))
            await self.children[0].finish()
            self.children[0].focus(scroll_visible=False)
            for message in reversed(self.messages[:-1]):
                if self.app.terminate:
                    self.working = False
                    break
                await self.mount(Message(self.chat, message), before=0)
                await self.children[0].finish()
            await self.children[0].wait_for_refresh()
            self.working = False
            self.anchor_visual(False)
        else:
            self.chat.text_area.focus()
