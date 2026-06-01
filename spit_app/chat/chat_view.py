# SPDX-License-Identifier: GPL-2.0
from textual.containers import VerticalScroll
from .message.message import Message
from .work import Work
from .lazy_load import LazyLoadMixIn
from spit_app.modal_screens import LoadingScreen

class ChatView(VerticalScroll, LazyLoadMixIn):
    BINDINGS = [
        ("ctrl+enter", "continue", "Continue"),
        ("u", "undo", "Undo"),
        ("r", "redo", "Redo")
    ]

    def __init__(self, chat) -> None:
        super().__init__()
        self.stop_worker = None
        self.lazy_scroll_home_end = 1
        self.chat = chat
        self.messages = self.chat.messages
        self.id = "chat-view"

    async def callback(self, signal: int) -> None:
        if signal == 0:
            self.chat.write_chat_history()
            self.chat.undo.append_undo("append", self.chat.messages[-1])
            await self.children[-1].finish()
            self.release_anchor()
            self.children[-1].processing = False
        elif signal == 1:
            await self.mount(Message(self.chat, self.messages[-1]))
            self.children[-1].processing = True
            self.anchor()
        elif signal == 2:
            if self.children[-1].display and not self.is_anchored:
                self.anchor()
            elif not self.children[-1].display and self.is_anchored:
                self.release_anchor()
            await self.children[-1].process()

    async def action_continue(self) -> None:
        if (self.messages[-1]["role"] == "user" or self.messages[-1]["role"] == "tool" or
            (self.messages[-1]["role"] == "assistant" and "tool_calls" in self.messages[-1])):
            self.lazy_scroll_home_end = 1
            work = Work(self.chat)
            self.chat.work = self.run_worker(work.work_stream())

    async def action_undo(self) -> None:
        await self.chat.undo.undo()

    async def action_redo(self) -> None:
        await self.chat.undo.redo()

    def action_scroll_home(self) -> None:
        self.lazy_scroll_home_end = -1

    def action_scroll_end(self) -> None:
        self.lazy_scroll_home_end = 1

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
        self.focus_message()

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        self.focus_message()

    def focus_message(self) -> None:
        height = 0
        if self.chat.text_area.has_focus:
            return None
        for message in self.displayed_children:
            if self.scroll_y > self.max_scroll_y - 4 and self.displayed_children[-1] is self.children[-1]:
                self.displayed_children[-1].focus(scroll_visible=False)
                break
            if self.scroll_y < 4 and self.displayed_children[0] is self.children[0]:
                message.focus(scroll_visible=False)
                break
            height += message.outer_size.height
            if height >= self.scroll_y + 4:
                if not message.has_focus and not message.has_focus_within:
                    message.focus(scroll_visible=False)
                break

    async def load(self) -> None:
        if self.messages:
            loading_screen = LoadingScreen()
            await self.app.push_screen(loading_screen)
            for message in self.messages:
                await self.mount(Message(self.chat, message, False))
            await loading_screen.dismiss()
            self.lazy_load_messages()
        else:
            self.lazy_load_messages()
            self.chat.text_area.focus()
