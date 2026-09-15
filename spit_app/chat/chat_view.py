# SPDX-License-Identifier: GPL-2.0
from textual.events import Focus
from .anchored_scroll import AnchoredScroll
from .textual_message import RemoveMessage
from .message.message import Message
from ..modal_screens import LoadingScreen
from .callback import CallbackMixIn
from .chat_view_actions import ChatViewActionsMixIn, bindings

class ChatView(ChatViewActionsMixIn, CallbackMixIn, AnchoredScroll):
    BLANK = True
    BINDINGS = bindings

    # The widget window: mounted children == messages[window_start:window_hi],
    # both ends free - the sliding window of UI-ONDEMAND-LOADING.md. WP-B held
    # this at the whole history (window_start 0, nothing ever evicted), which
    # is what made the accessor refactor provably behaviour-free; WP-C slides
    # it. `children[p]` is the widget of `messages[window_start + p]`, and
    # nothing outside this class' window block may compute the offset.
    INITIAL_WINDOW = 50       # load(): the last 50 messages (the plan's start;
                              # a settings surface may come later)
    PRUNE_MARGIN_FACTOR = 2   # prune(): rows kept on each side of the viewport
                              # = factor x viewport height. Rule 7 demands
                              # factor >= 1 (the clamp-zone guard); probe 7 was
                              # measured with 2 and held with zero jump frames.

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
        # Window state (instance state: the window slides per ChatView). lo is
        # stored; hi is derived, so it cannot drift from the widget tree (a
        # stored (lo, hi) tuple would be a second source of truth).
        self.window_start = 0
        # Re-entrancy guard for the page operations (load_older/load_newer and
        # prune). A trigger that fires while one is in flight asks for a page
        # the running operation is already growing; the answer is to drop it.
        self._window_page_op = False

    # --------------------------------------------------------------- accessors
    # The single seam between a MESSAGE index (a position in chat.messages, the
    # complete history) and the widget that projects it. Every index a caller
    # holds is a message index; a child position exists only inside this block.

    @property
    def window_hi(self) -> int:
        """One past the last MOUNTED message index. Derived from the child
        count on purpose: `window = [lo, hi)` with hi = lo + len(children) is
        the statement that the mounted range is contiguous, and deriving it
        keeps that statement from needing its own bookkeeping."""
        return self.window_start + len(self.children)

    @property
    def window(self) -> tuple[int, int]:
        """[lo, hi): the mounted children are exactly messages[lo:hi]."""
        return (self.window_start, self.window_hi)

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
        """The invariant of the sliding window: `children[p]` projects
        `messages[window_start + p]` - checked by dict identity - and the
        window stays inside the data.

        A method rather than an assert in the mutation paths because it holds
        at QUIESCENCE only: streaming appends a dict to `chat.messages` and
        posts the mount afterwards (work.py, endpoints), so mid-stream the data
        legitimately runs ahead of the widget tree - that gap is what
        `is_present` exists for. `unit:chat_smoke` asserts it after every step
        of the scripted walk, which is where it is true and where a drift is a
        bug; the windowed checks of `unit:chat_window` assert it after every
        page operation. (WP-B's arithmetic form `len(children) == len(messages)
        - window_start` is this with lo 0 and the tail intact; with the bottom
        prunable the identity form is what stays true.)
        """
        if self.window_start < 0:
            return False
        if self.window_start + len(self.children) > len(self.messages):
            return False
        position = self.window_start
        for child in self.children:
            if child.message is not self.messages[position]:
                return False
            position += 1
        return True

    # ------------------------------------------------------------ window moves
    # Everything below may move lo (and thus the whole mapping); nothing else
    # assigns window_start. Mounts above the top arm the one-shot top anchor
    # first, so the compensation lands in the same layout pass (rule 1);
    # mounts and evictions below need none (rule 2).

    async def _grow_up(self, count: int, render: bool = True) -> None:
        """Mount up to `count` messages above the window, anchor-armed.

        lo moves only after the batch: mid-operation the accessors keep
        answering for the old, still-consistent range rather than a half
        remapped one. Clamped at message 0 - the top of the history is not an
        error. `render=False` leaves the TARGET widget unfinished (the newest
        mounted is the target here); it is what the stream sites use, because
        the next message's content belongs to the stream, not to materialize.
        """
        count = min(count, self.window_start)
        if count <= 0:
            return
        lo = self.window_start
        target = lo - count
        self.arm_top_anchor()
        async with self.batch():
            for index in reversed(range(target, lo)):
                await self.mount(Message(self.chat, self.messages[index]), before=0)
                if render or index != target:
                    await self.children[0].finish()
        self.window_start = target

    async def _grow_down(self, count: int, render: bool = True) -> None:
        """Mount up to `count` messages below the window. No compensation:
        appending below the viewport moves nothing above it (rule 2), and the
        follow-bottom anchor, if the user is at the bottom, still wins the
        frame. Clamped at the tail of the data. `render=False` leaves the
        TARGET (the last widget mounted) unfinished; the gap it closes is
        always history and is always rendered."""
        hi = self.window_hi
        count = min(count, len(self.messages) - hi)
        if count <= 0:
            return
        last = hi + count - 1
        async with self.batch():
            for index in range(hi, hi + count):
                await self.mount(Message(self.chat, self.messages[index]))
                if render or index != last:
                    await self.last_child().finish()

    async def load_older(self, count: int) -> None:
        """A page of history above the window: the arm -> batch-mount ->
        (auto-)disarm dance at the top end."""
        if self._window_page_op:
            return None
        self._window_page_op = True
        try:
            await self._grow_up(count)
        finally:
            self._window_page_op = False

    async def load_newer(self, count: int) -> None:
        """A page of history below the window (the remount side of an evicted
        bottom - rule 3: holds, same frame)."""
        if self._window_page_op:
            return None
        self._window_page_op = True
        try:
            await self._grow_down(count)
        finally:
            self._window_page_op = False

    async def materialize(self, index: int, render: bool = True) -> Message:
        """Grow the window until messages[index] has a widget, and return it.

        The explicit last-message handler behind the three sharp edges of the
        coupling table (abort, submit, message_start): each addresses the last
        MESSAGE by data index and calls this, so a pruned end is closed before
        anything is finished or removed there. Widgets the window grows over
        are finished - a `Message` is a disposable projection of its dict, so
        re-entering the window re-renders from the dict (fact 5). The target
        itself is finished too unless `render=False`.

        Out of the data raises IndexError - the exception `children[index]`
        raised - because addressing a message that does not exist is a bug.
        """
        message = self.widget(index)
        if message is not None:
            return message
        if not 0 <= index < len(self.messages):
            raise IndexError(
                f"message {index} does not exist "
                f"({len(self.messages)} messages)")
        if index < self.window_start:
            await self._grow_up(self.window_start - index, render)
        else:
            await self._grow_down(index - self.window_hi + 1, render)
        return self.require_widget(index)

    def _prune_pinned(self, child: Message) -> bool:
        """Fact 5, the set `prune()` must never evict: the focused widget (or
        any widget holding focus within it - focus can sit on an inner
        Process), a widget in edit (its editing state lives INSIDE the widget),
        and - while the chat works - the last message (the streaming tail)."""
        if child.is_edit:
            return True
        if (child is self.focused_widget or child is self.focused_message
                or child.has_focus_within):
            return True
        if self.chat.is_working() and child is self.widget(len(self.messages) - 1):
            return True
        return False

    async def prune(self) -> None:
        """Release both ends back to the margin around the viewport.

        Eviction is strictly outside viewport +/- margin (margin = factor x
        viewport height, factor >= 1): the window always holds >= viewport +
        2 x margin rows of mounted content when the history has them, so a
        compensation never lands in the clamp zone (rule 7) and `scroll_y` is
        never clamped out of agreement with the view. Evicting ABOVE arms the
        one-shot anchor - the same event as a mount above with the sign flipped
        (rule 1, probe 7 / unit:anchored t13); evicting BELOW moves nothing and
        corrects nothing (rule 2, t14). The pinned set of fact 5 bounds each
        walk, which also keeps the eviction a strict prefix/suffix and the
        window contiguous. Mounted count is then a function of viewport +
        margin, never of history length - which is the point.

        A consequence recorded from WP-A: the anchor is chosen viewport-first
        and evictions are strictly outside the viewport, so prune never removes
        the widget the pin is anchored to.
        """
        if self._window_page_op or self.is_removing or not self.children:
            return None
        viewport = self.content_region
        if viewport.height <= 0:
            # Not laid out (a hidden Chat in #main, or never shown): the
            # regions to measure against are stale, and a hidden chat's window
            # is no eviction target. Keep it whole.
            return None
        margin = self.PRUNE_MARGIN_FACTOR * viewport.height
        above = [c for c in self.children if c.region.bottom <= viewport.y]
        below = [c for c in self.children if c.region.y >= viewport.bottom]

        evict_above = []
        budget = sum(c.region.height for c in above) - margin
        for child in above:
            if child.region.height > budget or self._prune_pinned(child):
                break
            evict_above.append(child)
            budget -= child.region.height

        evict_below = []
        budget = sum(c.region.height for c in below) - margin
        for child in reversed(below):
            if child.region.height > budget or self._prune_pinned(child):
                break
            evict_below.append(child)
            budget -= child.region.height

        if not evict_above and not evict_below:
            return None
        if evict_above:
            self.arm_top_anchor()
        async with self.batch():
            for child in evict_above:
                async with child.lock:
                    await child.remove()
            for child in evict_below:
                async with child.lock:
                    await child.remove()
        self.window_start += len(evict_above)

    # ----------------------------------------------------------------- mounting

    async def mount_message(self, index: int) -> None:
        if index == len(self.messages):
            # Unreachable and broken as it stands: messages[index] with
            # index == len(messages) is an IndexError. Both callers insert the
            # dict first, so index < len(messages); filed in WP-B, untouched.
            await self.mount(Message(self.chat, self.messages[index]))
        elif index < self.window_start:
            # A windowed insertion above the top: the widget goes on the front
            # and lo slides down, so the mounted range stays contiguous.
            await self.mount(Message(self.chat, self.messages[index]), before=0)
            self.window_start -= 1
        else:
            await self.mount(Message(self.chat, self.messages[index]),
                             before=self.child_position(index))

    async def on_remove_message(self, message: RemoveMessage) -> None:
        self.chat.undo.append_undo("remove", self.messages[message.index], message.index)
        child = self.widget(message.index)
        if child is not None:
            async with child.lock:
                await child.remove()
        elif message.index < self.window_start:
            # A removal BELOW the window (the streaming-error path removes
            # `messages[-1]`, which may already have been evicted): the data
            # shifts under the window, so lo slides with it.
            self.window_start -= 1
        del self.messages[message.index]
        self.chat.write_chat_history()
        if self.messages:
            if message.index == 0:
                index = 0
            else:
                index = message.index - 1
            neighbour = self.widget(index) or self.last_child()
            if neighbour is not None:
                neighbour.focus(scroll_visible=False)
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
        """Open at the bottom: mount the last `INITIAL_WINDOW` messages.

        The bottom anchor armed in __init__ keeps the view pinned through the
        batched mount - that IS the open-at-bottom UX, unchanged from the
        whole-history load(). No explicit `scroll_end` here on purpose:
        `scroll_end` funnels through `Widget._scroll_to`, which calls
        `release_anchor()` - calling it at open would release follow-bottom
        before the user ever touched the scroll, changing streaming behaviour.
        The window slides from here: `window_start` is the first mounted
        message, and the older history is a `load_older` away.
        """
        if self.messages:
            loading_screen = LoadingScreen()
            await self.app.push_screen(loading_screen)
            self.window_start = max(0, len(self.messages) - self.INITIAL_WINDOW)
            async with self.batch():
                for message in self.messages[self.window_start:]:
                    await self.mount(Message(self.chat, message))
                    await self.last_child().finish()
            loading_screen.dismiss()
