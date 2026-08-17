from .message.message import Message
from .textual_message import StreamCallback

class CallbackMixIn:
    def callback(self, message_index: int, signal: int) -> None:
        self.post_message(StreamCallback(message_index, signal))

    def is_present(self, index: int) -> bool:
        if index < len(self.children):
            return True
        return False

    async def message_finish(self, index: int) -> None:
        self.chat.write_chat_history()
        self.chat.undo.append_undo("insert", self.chat.messages[index], index)
        if self.is_present(index):
            async with self.children[index].lock:
                await self.children[index].finish()

    async def message_start(self, index: int) -> None:
        await self.mount(Message(self.chat, self.messages[index]))
        if self.is_present(index):
            async with self.children[index].lock:
                await self.children[index].wait_for_refresh()
                self.focus_message(index)

    def focus_message(self, index: int) -> None:
        if self.chat.display:
            self.children[index].focus(scroll_visible=False)
        else:
            self.children[index].set_focused_message()

    async def message_process(self, index: int) -> None:
        if self.is_present(index):
            async with self.children[index].lock:
                if self.display and (self.children[index].has_focus or self.children[index].has_focus_within):
                    await self.children[index].process()

    async def on_stream_callback(self, message: StreamCallback) -> None:
        if message.signal == 0:
            await self.message_finish(message.index)
        elif message.signal == 1:
            await self.message_start(message.index)
        elif message.signal == 2:
            await self.message_process(message.index)
