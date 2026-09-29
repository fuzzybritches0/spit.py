from .message.message import Message
from .textual_message import StreamCallback

class CallbackMixIn:
    def callback(self, message_index: int, signal: int) -> None:
        self.post_message(StreamCallback(message_index, signal))

    def is_present(self, index: int) -> bool:
        """Does message `index` have a widget? The window-aware question, and the
        only place the answer comes from: `widget()` (UI-ONDEMAND-LOADING.md WP-B).

        The pre-window form was `index < len(self.children)`, which answered True
        for a NEGATIVE index and then indexed the last child - the wrong widget.
        A negative index is not a message: every index that reaches here is a
        position in `chat.messages`. Filed in the WP-B entry; the one place where
        the accessor is deliberately narrower than the indexing it replaced.
        """
        return self.widget(index) is not None

    async def message_finish(self, index: int) -> None:
        self.chat.write_chat_history()
        self.chat.undo.append_undo("insert", self.chat.messages[index], index)
        message = self.widget(index)
        if message is not None:
            async with message.lock:
                await message.finish()

    async def message_start(self, index: int) -> None:
        # The third `children[-1]` sharp edge, addressed by data index: the
        # streaming message's dict exists but its widget is mounted only here,
        # and with a sliding window the bottom it lands on may have been
        # pruned while the model thought. `materialize` closes the gap below
        # the window (gap widgets are history: rendered from their dicts) and
        # mounts the TARGET unfinished (`render=False` - the stream owns the
        # target's content until signal 0). With the window whole this mounts
        # exactly what the plain `mount(...)` it replaced mounted, nothing more.
        message = await self.materialize(index, render=False)
        await message.wait_for_refresh()
        self.focus_message(index)

    def focus_message(self, index: int) -> None:
        message = self.require_widget(index)
        if self.chat.display:
            message.focus(scroll_visible=False)
        else:
            message.on_focus()

    async def message_process(self, index: int) -> None:
        message = self.widget(index)
        if message is None:
            return None
        async with message.lock:
            if self.display and (message.has_focus or message.has_focus_within):
                await message.process()

    async def on_stream_callback(self, message: StreamCallback) -> None:
        # A signal about a message that is NO LONGER A MESSAGE is a signal about a
        # reply that was taken back, and there is nothing here to do with it (P19
        # /WP-2). `post_message` only queues, so the signals a stream posted before
        # it died are still in this widget's queue when the reply is rolled back -
        # and both rollback callers delete by DATA index: `action_abort` (which
        # could already meet this, since cancelling the worker leaves the queue
        # behind) and `Work.stream_attempts`, which AWAITS `remove_message_at`
        # between attempts because the next request must not start on the corpse.
        # Without this guard the stale signal-1 reaches `message_start` ->
        # `materialize(index)` -> `self.messages[index]` on an index one past the
        # end: an IndexError out of a Textual message handler (measured, t14's
        # abort case). The guard fires ONLY on a reply that no longer exists:
        # signal 1 is posted immediately after `messages.append(...)`, and signals
        # 2 and 0 while that dict stands, so a live reply can never match it.
        if not 0 <= message.index < len(self.messages):
            return None
        if message.signal == 0:
            await self.message_finish(message.index)
            # The token counts on the chat-settings row, at the end of every
            # reply — the tool-loop calls included, since that recursion ends a
            # stream too. It is wired HERE and not as a handler on ChatSettings
            # because a StreamCallback is posted on this widget and a Textual
            # Message bubbles to ANCESTORS only: ChatSettings is a SIBLING of the
            # ChatView, so a handler of its own for this message is never called
            # (measured 2026-09-22 — a handler on ChatSettings receives nothing,
            # the one on Chat receives ('Chat', 0)). This branch is chosen over a
            # new handler on Chat because it is the one place that already knows
            # "signal 0, this reply is over": a handler on Chat fires for signals
            # 1 and 2 as well, i.e. once per streamed chunk, for a call needed
            # once; and a call sitting in the handler that is guaranteed to run
            # cannot be orphaned later by someone stopping the bubble — which is
            # exactly the invisible dead signal this step had to measure its way
            # around. refresh_usage() itself never blocks: the network question
            # it may start runs in a worker.
            self.chat.chat_settings.refresh_usage()
        elif message.signal == 1:
            await self.message_start(message.index)
        elif message.signal == 2:
            await self.message_process(message.index)
