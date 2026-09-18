# SPDX-License-Identifier: GPL-2.0
from textual.events import Focus
from .anchored_scroll import AnchoredScroll
from .textual_message import RemoveMessage
from .message.message import Message
from ..modal_screens import LoadingScreen
from .callback import CallbackMixIn
from .chat_view_actions import ChatViewActionsMixIn, bindings


# The settled-scroll debounce (WP-D). Textual 8.2.8 has no `scroll_ended` /
# `scroll_scheduled` hook at all: `Widget.is_scrolling` (widget.py:2586) is a
# 0.1 s "ended very recently" window, `_last_scroll_time` is the only other
# thing there is, so "the user stopped scrolling" has to be a timer of ours.
# 0.15 s sits above that window (a scroll still in flight never prunes) and is
# short enough to read as immediate; the suite's `settle()` costs 0.187 s, so
# one settle is enough to see it fire.
SCROLL_SETTLE_DELAY = 0.15


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
    TRIGGER_MARGIN_FACTOR = 1  # the scroll triggers: rows of REAL mounted child
                              # region on a side, below which that side is "at
                              # the window edge" and history is paged in. It is
                              # STRICTLY below PRUNE_MARGIN_FACTOR, which is the
                              # anti-oscillation invariant: a settled prune
                              # always leaves more history mounted on a side
                              # than a trigger asks for, so a page-in and a
                              # prune cannot chase each other across frames.
                              # Measured in rows of child regions, never in
                              # scroll_y / max_scroll_y - those are margins, not
                              # rows of content (rule 7's arithmetic identity
                              # does not hold: scroll_y 352 against 308 rows).

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
        # Re-entrancy guard for the page operations: load_older/load_newer and
        # prune, and - since WP-D - load() and materialize() as well. A scroll
        # trigger that fires while one is in flight asks for a page the running
        # operation is already growing, and the answer is to DROP the trigger
        # (it asks again on the next notch, or at the settle). The two entry
        # points that must never be dropped - opening a chat, and the stream
        # sites that address the last MESSAGE by data index - SAVE and RESTORE
        # the flag instead of clearing it, so they neither re-enter a page
        # operation nor let a trigger interleave a second mount batch with
        # their own.
        self._window_page_op = False
        # The settled-scroll debounce (WP-D): ONE timer, re-armed by every
        # scroll, whose callback prunes and re-checks the edges. None when no
        # settle is pending.
        self._settle_timer = None

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
        bottom - rule 3: holds, same frame).

        The one deliberate touch on follow-bottom in this whole WP, and the
        reason it needs a paragraph: `anchor()` is never armed or disarmed
        here, but Textual RE-ARMS it whenever the view sits at `max_scroll_y`
        (`Widget._check_anchor`, widget.py:823) - and `max_scroll_y` is the
        WINDOW's bottom, not the chat's tail. So a reader parked at the bottom
        of a mid-history window has the anchor armed, and mounting below pulls
        the view down to the new bottom (measured: 39 -> 239 == the new max,
        one correction, no intermediate frame) - which would drag away anyone
        who was not reading the tail at all. Release first, therefore, but
        ONLY when this page will not reach the tail: a page that does reach it
        IS the tail, and following the tail is exactly what the anchor is for
        (measured both ways: not-reach 39 -> 39 HELD, reach 39 -> 383 PULLED).
        Nothing is stranded by the release - the compositor re-arms the moment
        the view lands on the true tail again.
        """
        if self._window_page_op:
            return None
        self._window_page_op = True
        try:
            if (self._anchored and not self._anchor_released
                    and self.window_hi + count < len(self.messages)):
                self.release_anchor()
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
        # From here the window really grows, so it holds the page-op guard.
        # Save/restore rather than clear: this is called from the stream sites
        # (abort, submit, message_start) and a scroll trigger landing in the
        # middle of it would run a SECOND mount batch over the same range. The
        # save half matters as much as the set half - a caller that already
        # holds the guard must not have it released under it, because the
        # trigger that would have been dropped then gets through.
        was_page_op = self._window_page_op
        self._window_page_op = True
        try:
            if index < self.window_start:
                await self._grow_up(self.window_start - index, render)
            else:
                await self._grow_down(index - self.window_hi + 1, render)
        finally:
            self._window_page_op = was_page_op
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

        WP-D: it TAKES the re-entrancy guard, it does not only ask for it. WP-C
        could get away with checking it, because there prune was only ever the
        second half of an explicit sequence; WP-D runs it from the settled-scroll
        `set_timer` callback, which is a different asyncio task from the
        `call_after_refresh` page operation, so the two interleave at prune's
        `await child.remove()` points. That is not a cosmetic overlap: `_grow_up`
        writes lo ABSOLUTELY (`window_start = lo - count`, from the value it
        read) while prune adds to it afterwards
        (`window_start += len(evict_above)`), so a page-above landing inside the
        removal batch leaves the eviction count added to the wrong base and the
        mounted range keeps a hole in the middle of the history - a state every
        accessor then reads wrong, not a transient. Measured: the interleave
        forced at that point corrupts the window 2 times out of 3
        (/tmp/wp-d3-probe-interleave4.py); with the guard taken, the page
        operation drops and the window survives.
        """
        if self._window_page_op or self.is_removing or not self.children:
            return None
        self._window_page_op = True
        try:
            await self._release_outside_the_margin()
        finally:
            self._window_page_op = False

    async def _release_outside_the_margin(self) -> None:
        """`prune()`'s walk and batch, run under the guard.

        Split out because the guard has to cover the whole removal batch - the
        await points inside it are exactly where a page operation would interleave
        - and because `prune()`'s own first line asks the guard, so the setter
        cannot live in the same body as the question.

        `window_start` moves only AFTER the batch, for the same reason the mount
        batches do: mid-operation the accessors keep answering for the old,
        still-consistent range. The pair (batch, then lo) is what must not be
        interrupted, and since WP-D the guard is what guarantees it: the two
        `window_start` writes are of different kinds - this one ADDS to the value
        the batch started from, `_grow_up` ASSIGNS an absolute one.
        """
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

    # ------------------------------------------------------------ scroll triggers
    # WP-D: the view asks for history, the window answers. Two events drive it -
    # a scroll that lands NEAR A WINDOW EDGE pages history in, and a scroll that
    # SETTLES prunes the far end back to the margin.
    #
    # Why a timer for "settled": Textual 8.2.8 has no scroll_ended hook at all
    # (SCROLL_SETTLE_DELAY above). Why the page operation goes through
    # `call_after_refresh`: a mount must never re-enter the layout pass that is
    # reporting the scroll, and an async callback posted there IS awaited.
    #
    # Why the trigger can never see its own work: a scroll_y correction - ours
    # and the compositor's follow-bottom - is written with `DOM.set_reactive`,
    # which does not invoke watchers (dom.py:249). Measured: `load_older(20)` is
    # 1 correction and 0 watch calls; `load()`'s follow-bottom writes are 0
    # watch calls. So `watch_scroll_y` only ever sees USER motion, and the
    # guards in `_triggers_frozen` are about the app's other mutations, not
    # about feedback from this one.

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        # super() FIRST and always: AnchoredScroll.watch_scroll_y re-baselines
        # the pin after a landed scroll and Widget.watch_scroll_y is what
        # re-arms follow-bottom. Whatever the window decides about this scroll,
        # the container has already decided about it.
        super().watch_scroll_y(old_value, new_value)
        if round(old_value) == round(new_value):
            return                     # sub-row jitter: nothing moved
        if self._triggers_frozen():
            return
        self._arm_scroll_settle()
        # Deliberately no edge test HERE, and the callback takes no argument:
        # the children's regions are one frame STALE while a scroll is being
        # reported, so a decision taken at watch time is a decision taken on
        # the previous frame (measured - the fresh-looking numbers say `None`
        # and the answer is `older` once the frame lands). Posting unconditionally
        # and measuring in the callback is also what keeps the true window
        # bottom from starving: at a scroll LIMIT the wheel does not move
        # scroll_y at all, so it never reaches here, and the settle's own
        # re-check is then the only thing that can page history back in.
        self.call_after_refresh(self._load_at_edge)

    def _triggers_frozen(self) -> bool:
        """True while a scroll event must not touch the window.

        A page operation already in flight (the trigger would ask for a page the
        running operation is growing); a removal in progress; an edit, where
        fact 5 puts unloading out of reach entirely; the chat working, where the
        streaming tail must not be evicted and the bottom of the window is
        moving anyway; and the two ways a view has no geometry to measure
        against - not mounted, or laid out at zero height, which is the hidden
        Chat in #main (TRAPS #24: there, every viewport computation is
        vacuous, so the only safe answer is to do nothing).
        """
        if self._window_page_op or self.is_removing or self.is_edit:
            return True
        if self.chat.is_working():
            return True
        if not self.is_mounted or self.content_region.height <= 0:
            return True
        return False

    def _page_edge(self) -> str | None:
        """Which page operation the geometry asks for, or None.

        Thresholds in ROWS OF REAL CHILD REGION outside the viewport, never in
        `scroll_y` / `max_scroll_y - scroll_y`: those are margins of the WINDOW,
        and they disagree with the row counts by dozens of rows (measured 352
        against 308). Each side is asked only while it still HAS history, so
        the true ends stop cleanly instead of mounting nothing forever.
        """
        if self.window_start == 0 and self.window_hi >= len(self.messages):
            return None                      # the whole history is mounted
        viewport = self.content_region
        trigger = self.TRIGGER_MARGIN_FACTOR * viewport.height
        if self.window_start > 0:
            above = sum(child.region.height for child in self.children
                        if child.region.bottom <= viewport.y)
            if above < trigger:
                return "older"
        if self.window_hi < len(self.messages):
            below = sum(child.region.height for child in self.children
                        if child.region.y >= viewport.bottom)
            if below < trigger:
                return "newer"
        return None

    def _page_count(self) -> int:
        """How many messages a page holds: enough of them to cover the PRUNE
        margin, estimated from the MEAN mounted height, clamped to
        [1, INITIAL_WINDOW].

        The mean is the estimate because a page must refill what a settle
        releases, and what a settle releases is measured in rows. The upper
        clamp is the batch size the app already proved it could mount at open;
        the lower one means a chat of very tall messages still pages (slowly)
        rather than asking for zero messages and starving at the edge.
        """
        heights = [child.region.height for child in self.children]
        total = sum(heights)
        if not heights or total <= 0:
            return self.INITIAL_WINDOW // 2
        mean_height = total / len(heights)
        margin = self.PRUNE_MARGIN_FACTOR * self.content_region.height
        return max(1, min(self.INITIAL_WINDOW, int(margin / mean_height) + 1))

    async def _load_at_edge(self) -> None:
        """Page history in on whichever side the LANDED frame is short of, if any.

        The frozen state is re-checked here and not trusted from the watcher: a
        refresh is an eternity in this app, and a work run, an edit or a removal
        may well have started in it. Arming the settle afterwards is what gives
        a page that came in for a single wheel notch its prune.
        """
        if self._triggers_frozen():
            return
        edge = self._page_edge()
        if edge is None:
            return
        count = self._page_count()
        if edge == "older":
            await self.load_older(count)
        else:
            await self.load_newer(count)
        # Prune after every LOAD, and NOT another settle timer - both halves of
        # that are load-bearing.
        #
        # The prune: the settle timer is re-armed by EVERY notch, so a scroll that
        # never stops never settles, and its page operations would mount forever
        # (measured: 200 uninterrupted wheel-ups with the settle as the only prune
        # reach 58 mounted widgets and still climbing, against 11-15 with this -
        # the mounted count is a function of the viewport, never of how long the
        # wheel keeps turning). This is the plan's "prune() after every load".
        # The anti-oscillation invariant makes it safe rather than a chase: a
        # settled side keeps 2 viewports of rows and a trigger asks for 1, so the
        # page that just arrived is exactly what the prune refuses to evict.
        #
        # Not re-arming the settle: the only reason a page operation used to re-arm
        # it was to give the page its prune, and it now has that prune inline. What
        # re-arming instead did was chain: settle -> prune -> page in -> re-arm ->
        # settle, and a single 30-notch burst unwound 18 of those (measured, t11 of
        # the suite) - a tail of prunes running for seconds after the user stopped,
        # each one a layout pass. Only a SCROLL arms a settle.
        await self.prune()

    def _arm_scroll_settle(self) -> None:
        """(Re-)arm the ONE settle timer: a scroll in flight prunes ONCE, after
        its last notch, not once per notch."""
        if self._settle_timer is not None:
            self._settle_timer.stop()
        self._settle_timer = self.set_timer(SCROLL_SETTLE_DELAY, self._scroll_settled)

    async def _scroll_settled(self) -> None:
        """The scroll stopped: release both ends to the margin, then look at the
        edges again.

        The second half is not redundant with the watcher, and the reason is a
        measured starvation. A settled prune can leave the view CLAMPED at the
        new window bottom - `max_scroll_y` is the window's, not the history's -
        and from there the wheel cannot ask for anything: at a scroll limit a
        notch does not change `scroll_y`, so it fires no watcher at all
        (measured: 0 watch calls at a pruned window bottom with 240 messages
        unmounted below). The settle is the last event that ever fires in that
        state, so it is where the re-check has to live.
        """
        self._settle_timer = None
        if self._triggers_frozen():
            return
        await self.prune()
        await self._load_at_edge()

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
        # Guarded like a page operation, and for the WP-D reason: the mount
        # below is the biggest batch the widget ever takes, and a scroll that
        # arrives while it runs must not interleave a trigger's page op with
        # it. Save/restore, not clear: `load()` is called from the chat-open
        # path, which is not itself a page operation and must be left as it was
        # found.
        was_page_op = self._window_page_op
        self._window_page_op = True
        try:
            if self.messages:
                loading_screen = LoadingScreen()
                await self.app.push_screen(loading_screen)
                self.window_start = max(0, len(self.messages) - self.INITIAL_WINDOW)
                async with self.batch():
                    for message in self.messages[self.window_start:]:
                        await self.mount(Message(self.chat, message))
                        await self.last_child().finish()
                loading_screen.dismiss()
        finally:
            self._window_page_op = was_page_op
