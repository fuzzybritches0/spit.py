# SPDX-License-Identifier: GPL-2.0
from textual.events import Focus
from textual.containers import VerticalScroll
from .textual_message import RemoveMessage
from .message.message import Message
from ..modal_screens import LoadingScreen
from .callback import CallbackMixIn
from .chat_view_actions import ChatViewActionsMixIn, bindings

class ChatView(ChatViewActionsMixIn, CallbackMixIn, VerticalScroll):
    BLANK = True
    BINDINGS = bindings

    # The widget window: the mounted children are exactly
    # `messages[window_start:]`. WP-B hard-wires the whole history (0), which is
    # what makes every accessor below the identity translation of the
    # `children[...]` it replaced - the refactor is behaviour-free by
    # construction and the differential in `tests/unit/chat_smoke/` is the proof
    # (TRAPS #14/#18). WP-C turns the constant into the sliding window's `lo`;
    # nothing outside these accessors may compute the offset.
    window_start = 0

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

    # --------------------------------------------------------------- accessors
    # The single seam between a MESSAGE index (a position in chat.messages, the
    # complete history) and the widget that projects it. Every index a caller
    # holds is a message index; a child position exists only inside this block.

    def widget(self, index: int) -> Message | None:
        """The widget projecting messages[index], or None when it is not mounted.

        Out of window is an ordinary answer here: an update to an unmounted
        message is data-only, and the widget rebuilds from the dict on re-entry
        (UI-ONDEMAND-LOADING.md, facts 5 and 6).
        """
        position = index - self.window_start
        if 0 <= position < len(self.children):
            return self.children[position]
        return None

    def require_widget(self, index: int) -> Message:
        """`widget(index)` for the sites that address a message that must be
        mounted: raises IndexError out of window, exactly as `children[index]`
        did before there was a window. The failure is a bug (or, once WP-C
        slides the window, a missing `materialize`), never a state to absorb."""
        message = self.widget(index)
        if message is None:
            raise IndexError(
                f"message {index} is not mounted "
                f"(window_start {self.window_start}, {len(self.children)} children)")
        return message

    def widget_index(self, widget: Message) -> int | None:
        """The message index a mounted widget projects, or None if it is not one
        of ours. The reverse of `widget`; window-aware because a child position
        says nothing once either end can be evicted."""
        try:
            position = self.children.index(widget)
        except ValueError:
            return None
        return position + self.window_start

    def child_position(self, index: int) -> int | None:
        """Where messages[index] sits among the children - the int `mount(before=)`
        takes - or None when the index is beyond the mounted range."""
        position = index - self.window_start
        if 0 <= position <= len(self.children):
            return position
        return None

    def last_child(self) -> Message | None:
        """The last MOUNTED widget, or None when nothing is mounted.

        Deliberately NOT the last chat message: `children[-1]` was the loaded gun
        of the coupling surface, and it is still a legitimate thing to want here
        (focus what the user was last shown, finish the widget just mounted). A
        site that means the last MESSAGE says so with `widget(len(messages) - 1)`
        - and once WP-C prunes the bottom, with `materialize` as well.
        """
        return self.children[-1] if self.children else None

    def window_consistent(self) -> bool:
        """The invariant: `len(children) == len(messages) - window_start`.

        A method rather than an assert in the mutation paths because the
        equality holds at QUIESCENCE only: streaming appends a dict to
        `chat.messages` and posts the mount afterwards (work.py, endpoints), so
        mid-stream the data legitimately runs ahead of the widget tree - that
        gap is what `is_present` exists for. `unit:chat_smoke` asserts it after
        every step of the scripted walk, which is where it is true and where a
        drift is a bug.
        """
        return len(self.children) == len(self.messages) - self.window_start

    # ----------------------------------------------------------------- mounting

    async def mount_message(self, index: int) -> None:
        if index == len(self.messages):
            # Unreachable and broken as it stands: messages[index] with
            # index == len(messages) is an IndexError. Both callers insert the
            # dict first, so index < len(messages); filed in WP-B, untouched.
            await self.mount(Message(self.chat, self.messages[index]))
        else:
            await self.mount(Message(self.chat, self.messages[index]),
                             before=self.child_position(index))

    async def on_remove_message(self, message: RemoveMessage) -> None:
        self.chat.undo.append_undo("remove", self.messages[message.index], message.index)
        child = self.require_widget(message.index)
        async with child.lock:
            await child.remove()
        del self.messages[message.index]
        self.chat.write_chat_history()
        if self.messages:
            if message.index == 0:
                index = 0
            else:
                index = message.index - 1
            self.require_widget(index).focus(scroll_visible=False)
        elif not self.messages and not self.is_edit:
            self.chat.text_area.focus()
        else:
            self.focus()
        self.is_removing = False

    def on_focus(self, event: Focus) -> None:
        event.prevent_default()
        self.enter()

    def enter(self) -> None:
        self.ensure_is_highlighted()
        self.chat.text_area.was_focused = False
        self.focus_this()
        self.set_active()

    def focus_this(self) -> None:
        if self.children:
            if self.focused_widget:
                self.focused_widget.focus(scroll_visible=False)
            else:
                self.last_child().focus(scroll_visible=False)

    def set_active(self) -> None:
        self.chat.settings.active_chat = self.chat.id
        self.chat.settings.save()

    def ensure_is_highlighted(self) -> None:
        side_panel = self.app.query_one("#side-panel")
        side_panel.can_focus = False
        index = side_panel.get_option_index(self.chat.id)
        side_panel.highlighted = index

    def on_worker_state_changed(self) -> None:
        self.refresh_bindings()

    async def load(self) -> None:
        if self.messages:
            loading_screen = LoadingScreen()
            await self.app.push_screen(loading_screen)
            async with self.batch():
                for message in self.messages:
                    await self.mount(Message(self.chat, message))
                    await self.last_child().finish()
            loading_screen.dismiss()
