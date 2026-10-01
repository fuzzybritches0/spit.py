# SPDX-License-Identifier: GPL-2.0
from textual.events import Focus
from textual.containers import VerticalScroll
from .textual_message import RemoveMessage
from .message.message import Message
from ..modal_screens import LoadingScreen
from .callback import CallbackMixIn
from .chat_view_actions import ChatViewActionsMixIn, bindings

# The widget tree is the WHOLE history: `children[i] is Message(messages[i])`
# for every i, from the first message to the last. That is the invariant every
# index below assumes, and it is what the app ran on before the sliding-window
# experiment of `doc/UI-ONDEMAND-LOADING.md` (WP-A..WP-F, 2026-09-14..09-20).
# That experiment is REVERTED (DECISIONS 89): the window bounded the mounted
# count and cost the thing the count was bounded FOR - wheel-scrolling froze
# for as long as it took to mount and render a page (0.6-0.7 s per notch
# measured headless, worse with real messages), the position jumped when a
# settle pruned the far end, and nothing paged or pruned at all while the chat
# worked, which is exactly when a long tool loop makes the tree grow. The
# numbers and the four failure modes are in DECISIONS 89; the route question
# is P8, reopened.
class ChatView(ChatViewActionsMixIn, CallbackMixIn, VerticalScroll):
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

    async def mount_message(self, index: int) -> Message:
        """Mount the widget of `messages[index]` and return it, UNFINISHED.

        PRECONDITION: the dict is already in `messages[index]` - both callers
        (`message/actions.py`'s add flows, `undo._insert`) insert first and then
        ask for the widget, which is what makes `index` a data index and lets the
        neighbour be looked up once. The widget comes back because the callers
        finish, status-update and focus THAT widget: a second lookup of the same
        index is a second chance to address a different child.

        An index the data does not have raises IndexError, which is what
        indexing `messages[index]` did before this method bounds-checked.
        """
        if not 0 <= index < len(self.messages):
            raise IndexError(
                f"message {index} does not exist "
                f"({len(self.messages)} messages)")
        if index < len(self.children):
            await self.mount(Message(self.chat, self.messages[index]), before=index)
        else:
            await self.mount(Message(self.chat, self.messages[index]))
        return self.children[index]

    def focus_after_removal(self, index: int) -> None:
        """Where the focus goes when `messages[index]` has just been removed.

        The ONE rule both removal sites answer with (`on_remove_message` and
        `undo._remove`), so the two can never disagree about where the cursor
        goes after a message disappears: the message that took the vacated
        position if there is one, else the message before it; the text area
        when the chat is empty and not in edit mode, the view itself in edit.
        """
        if not self.messages:
            if self.is_edit:
                self.focus()
            else:
                self.chat.text_area.focus()
            return
        if not self.children:
            # The tree is empty while the data outlives it - only reachable
            # while a removal batch is still landing. The view is then the only
            # thing that can hold the cursor.
            self.focus()
            return
        neighbour = (self.children[index] if index < len(self.children)
                     else self.children[index - 1])
        neighbour.focus(scroll_visible=False)

    async def remove_message_at(self, index: int) -> None:
        """Remove `messages[index]` from the data AND the widget tree, completely,
        and be finished when this returns.

        The ONE rollback (P19/WP-2): one body, reached by `on_remove_message` for
        every posted `RemoveMessage` - the message-level remove action, and the
        retry loop between endpoint attempts (`Work.roll_back_attempt`, which
        posts and then WAITS for the data to move, because the next request must
        not start while the corpse still stands).

        It is reached through the queue and not around it: called straight from
        the worker it deletes the data while the dead attempt's own
        `StreamCallback`s are still in this widget's queue, and the queued
        signal-1 then addresses an index one past the end. The queue is FIFO, so
        the removal posted here runs AFTER those signals and sees the dict it is
        about. What the seam buys is that both callers share one rollback, so the
        undo record, the widget, the write and the focus rule cannot drift
        between them.

        Everything a removal owns is here and nowhere else: the undo record, the
        widget removal under the child's own lock, the data delete, the write to
        disk, the ONE focus rule, the `is_removing` release.
        """
        # The child is looked up tolerantly, and the case that tolerates is NOT
        # a bug: a view with no widget here has nothing on screen to take back,
        # and this method's job is the DATA. It happens whenever the tree does
        # not mirror the data - a ChatView that never ran `load()` (the suites
        # that drive `Work` over a fixture chat, `unit:endpoints`' retry loop),
        # or a mount still in flight. It cannot arrive through the user's own
        # remove, which starts at a widget.
        self.chat.undo.append_undo("remove", self.messages[index], index)
        child = self.children[index] if index < len(self.children) else None
        if child is not None:
            async with child.lock:
                await child.remove()
        del self.messages[index]
        self.chat.write_chat_history()
        if child is not None:
            # Focus moves only when a widget actually left the tree. On a
            # data-only removal nothing the reader can see has changed, and
            # moving the cursor then would drag it away from where they are.
            self.focus_after_removal(index)
        self.is_removing = False

    async def on_remove_message(self, message: RemoveMessage) -> None:
        # The posted message and the awaited call are ONE operation now, so the two
        # removal sites cannot drift: `Work` awaits `remove_message_at` between
        # endpoint attempts, where a queued handler is not an ordering it can use.
        await self.remove_message_at(message.index)

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
                self.children[-1].focus(scroll_visible=False)

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
        # The whole history, every time, as this method has always done it. It
        # is slow on a long chat (a 5k-message chat measured 115-187 s headless,
        # DECISIONS 76 (a)) and that is the real problem P8 was written for; it
        # is a MOUNT-time cost the user waits through ONCE with a loading screen,
        # not a per-notch cost paid for the rest of the session, which is what
        # the window traded it for.
        if self.messages:
            loading_screen = LoadingScreen()
            await self.app.push_screen(loading_screen)
            async with self.batch():
                for message in self.messages:
                    await self.mount(Message(self.chat, message))
                    await self.children[-1].finish()
            loading_screen.dismiss()
