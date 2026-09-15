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
        await self.mount(Message(self.chat, self.messages[index]))
        message = self.widget(index)
        if message is not None:
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
        if message.signal == 0:
            await self.message_finish(message.index)
        elif message.signal == 1:
            await self.message_start(message.index)
        elif message.signal == 2:
            await self.message_process(message.index)
