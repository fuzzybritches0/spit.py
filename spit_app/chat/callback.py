from .message.message import Message
from .textual_message import StreamCallback

class CallbackMixIn:
    def callback(self, message_index: int, signal: int) -> None:
        self.post_message(StreamCallback(message_index, signal))

    def is_present(self, index: int) -> bool:
        """Does message `index` already have a widget?

        The whole history is mounted, so the answer is the child count - with
        the one exception this method exists for: while a reply streams, its
        dict is appended BEFORE signal 1 mounts its widget, so the data runs one
        ahead of the tree and `message_finish`/`message_process` legitimately
        meet an index with no child yet.

        The bound is two-sided (`0 <=`) and not the `index < len(...)` this site
        had: a NEGATIVE index passed that test and then indexed from the END of
        the child list - the wrong widget, silently. A negative index is not a
        message; every index that reaches here is a position in `chat.messages`.
        """
        return 0 <= index < len(self.children)

    async def message_finish(self, index: int) -> None:
        self.chat.write_chat_history()
        self.chat.undo.append_undo("insert", self.chat.messages[index], index)
        if self.is_present(index):
            async with self.children[index].lock:
                await self.children[index].finish()

    async def message_start(self, index: int) -> None:
        await self.mount(Message(self.chat, self.messages[index]))
        if self.is_present(index):
            await self.children[index].wait_for_refresh()
            self.focus_message(index)

    def focus_message(self, index: int) -> None:
        if self.chat.display:
            self.children[index].focus(scroll_visible=False)
        else:
            self.children[index].on_focus()

    async def message_process(self, index: int) -> None:
        if self.is_present(index):
            async with self.children[index].lock:
                if self.display and (self.children[index].has_focus or self.children[index].has_focus_within):
                    await self.children[index].process()

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
        # `self.messages[index]` on an index one past the end: an IndexError out of
        # a Textual message handler (measured, t14's abort case). The guard fires
        # ONLY on a reply that no longer exists: signal 1 is posted immediately
        # after `messages.append(...)`, and signals 2 and 0 while that dict stands,
        # so a live reply can never match it.
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
