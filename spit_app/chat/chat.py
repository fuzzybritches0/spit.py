# SPDX-License-Identifier: GPL-2.0
import json
from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from .undo import Undo
from .chat_text_area import ChatTextArea
from .chat_view import ChatView
from spit_app.overlays.loading_screen import LoadingScreen

class Chat(Vertical):
    BINDINGS = [
        ("ctrl+escape", "abort", "Abort"),
        ("escape", "change_focus", "Focus")
    ]
    signal = reactive(-1, always_update=True, init=False)

    def __init__(self, id) -> None:
        super().__init__()
        self.settings = self.app.settings
        self.classes = "chat"
        self.id = id
        chat = id + ".json"
        with open(self.settings.data_path / chat, "r") as file:
            content = json.load(file)
        self.chat_ctime = content["ctime"]
        self.chat_desc = content["desc"]
        self.chat_endpoint = content["endpoint"]
        self.chat_prompt = content["prompt"]
        self.messages = content["messages"]
        self.work = None
        self.edit = False
        self.chat_view = ChatView(self)
        self.text_area = ChatTextArea(self)
        self.undo = Undo(self)
        self.callback_busy = False
        self.callback_0_pending = False

    def is_working(self) -> bool:
        if self.work and self.work.is_running:
            return True
        return False

    def compose(self) -> ComposeResult:
        yield self.chat_view
        yield self.text_area

    def callback(self, signal: int) -> None:
        self.signal = signal

    async def watch_signal(self, before: int, now: int) -> None:
        if now == 0:
            self.write_chat_history()
            if not self.callback_busy:
                await self.chat_view.children[-1].finish()
            else:
                self.callback_0_pending = True
        elif now == 1:
            self.callback_busy = True
            await self.chat_view.mount_message(self.messages[-1])
            self.callback_busy = False
        elif now == 2:
            if not self.callback_busy and not self.callback_0_pending:
                self.callback_busy = True
                await self.chat_view.children[-1].process()
                self.callback_busy = False

    async def on_worker_state_changed(self) -> None:
        if not self.work.is_running and self.callback_0_pending:
            await self.chat_view.children[-1].finish()
            self.callback_0_pending = False
        self.refresh_bindings()

    def write_chat_history(self) -> None:
        file_name = self.id + ".json"
        file = self.settings.data_path / file_name
        content = {}
        content["ctime"] = self.chat_ctime
        content["desc"] = self.chat_desc
        content["endpoint"] = self.chat_endpoint
        content["prompt"] = self.chat_prompt
        content["messages"] = self.messages
        with open(file, "w") as f:
            json.dump(content, f)
    
    def save_message(self, umessage: dict) -> None:
        self.messages.append(umessage)
        self.undo.append_undo("append", umessage)
        self.write_chat_history()

    async def remove_last_message(self) -> None:
        del self.messages[-1]
        await self.chat_view.children[-1].remove()

    def action_change_focus(self) -> None:
        self.text_area.focus()

    async def action_abort(self) -> None:
        self.work.cancel()
        del self.messages[-1]
        await self.chat_view.children[-1].remove()
        self.refresh_bindings()

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "abort":
                return self.is_working()
        return True

    async def update_message(self, index: int) -> None:
        await self.chat_view.children[index].reset()
        await self.chat_view.children[index].finish()

    async def on_mount(self) -> None:
        if not self.messages:
            self.text_area.focus()
        else:
            loading_screen = LoadingScreen()
            await self.app.push_screen(loading_screen)
            for message in self.messages:
                await self.chat_view.mount_message(message)
            await loading_screen.dismiss()

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        self.app.query_one("#side-panel").can_focus = False
        if event.control is self.chat_view:
            if self.chat_view.focused_message:
                self.chat_view.focused_message.focus(scroll_visible=False)
            elif not self.messages:
                self.text_area.focus()
        elif not event.control is self.text_area:
            self.chat_view.focused_message = event.control
