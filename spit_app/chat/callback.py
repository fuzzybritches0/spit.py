from .message.message import Message
from .textual_message import StreamCallback

class CallbackMixIn:
    def callback(self, message_index: int, signal: int) -> None:
        self.post_message(StreamCallback(message_index, signal))

    async def message_finish(self, index: int) -> None:
        self.chat.write_chat_history()
        self.chat.undo.append_undo("insert", self.chat.messages[index], len(self.messages))
        await self.children[index].finish()

    async def message_start(self, index: int) -> None:
        await self.mount(Message(self.chat, self.messages[index]))
        self.children[index].focus(scroll_visible=False)

    async def message_process(self, index: int) -> None:
        await self.children[index].process()

    async def on_stream_callback(self, message: StreamCallback) -> None:
        if message.signal == 0:
            await self.message_finish(message.index)
        elif message.signal == 1:
            await self.message_start(message.index)
        elif message.signal == 2:
            await self.message_process(message.index)
