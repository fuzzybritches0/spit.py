# SPDX-License-Identifier: GPL-2.0
from textual.events import Focus
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
        ("r", "redo", "Redo"),
        ("a", "add", "Add")
    ]

    def __init__(self, chat) -> None:
        super().__init__()
        self.anchor()
        self.chat = chat
        self.cs = chat.cs
        self.messages = self.chat.messages
        self.focused_widget = None
        self.focused_message = None
        self.is_edit = False
        self.is_removing = False
        self.id = "chat-view"

    async def mount_message(self, index: int) -> None:
        if index == len(self.messages):
            await self.mount(Message(self.chat, self.messages[index]))
        else:
            await self.mount(Message(self.chat, self.messages[index]), before=index)

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
                if not "tool_calls" in self.messages[-1]:
                    return False
            if not self.messages[-1]["content"]:
                return False
            if not self.messages[-1]["content"][0]["text"]:
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

    async def on_remove_message(self, message: RemoveMessage) -> None:
        self.chat.undo.append_undo("remove", self.messages[message.index], message.index)
        await self.children[message.index].remove()
        del self.messages[message.index]
        self.chat.write_chat_history()
        if self.messages:
            if message.index == 0:
                index = 0
            else:
                index = message.index - 1
            self.children[index].focus(scroll_visible=False)
        elif not self.messages and not self.is_edit:
            self.chat.text_area.focus()
        else:
            self.focus()
        self.is_removing = False

    def on_descendant_focus(self) -> None:
        if self.chat.display:
            self.chat.text_area.was_focused = False
            self.focused_widget = self.app.focused

    def on_focus(self, event: Focus|None) -> None:
        event.prevent_default()
        self.focus_message()

    def set_active(self) -> None:
        self.chat.settings.active_chat = self.chat.id
        self.chat.settings.save()
        self.ensure_is_highlighted()
        if self.children:
            self.children[-1].focus(scroll_visible=False)
            self.chat.text_area.was_focused = False

    def ensure_is_highlighted(self) -> None:
        side_panel = self.app.query_one("#side-panel")
        side_panel.can_focus = False
        index = side_panel.get_option_index(self.chat.id)
        side_panel.highlighted = index

    def focus_message(self) -> None:
        self.ensure_is_highlighted()
        if self.focused_widget:
            self.focused_widget.focus(scroll_visible=False)

    async def on_worker_state_changed(self) -> None:
        self.refresh_bindings()

    async def load(self) -> None:
        if self.messages:
            loading_screen = LoadingScreen()
            await self.app.push_screen(loading_screen)
            async with self.batch():
                for message in self.messages:
                    await self.mount(Message(self.chat, message))
                    await self.children[-1].finish()
            loading_screen.dismiss()
        else:
            self.chat.text_area.focus()
        self.set_active()
