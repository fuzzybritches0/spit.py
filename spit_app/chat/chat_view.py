# SPDX-License-Identifier: GPL-2.0
from textual.events import Focus
from textual.containers import VerticalScroll
from .textual_message import RemoveMessage
from .message.message import Message
from ..modal_screens import LoadingScreen
from .callback import CallbackMixIn
from .chat_view_actions import ChatViewActionsMixIn, bindings

class ChatView(ChatViewActionsMixIn, VerticalScroll, CallbackMixIn):
    BLANK = True
    BINDINGS = bindings

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

    def on_worker_state_changed(self) -> None:
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
