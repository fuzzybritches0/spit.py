# SPDX-License-Identifier: GPL-2.0
from .message.message import Message

class Undo:
    def __init__(self, chat) -> None:
        self.chat = chat
        self.chat_view = chat.chat_view
        self.app = chat.app
        self.messages = chat.messages
        self.undo_list = []
        self.undo_index = -1

    async def _change(self, operation: str,message: dict, index: int) -> None:
        temp_message = self.messages[index].copy()
        self.messages[index] = message.copy()
        self.undo_list[self.undo_index] = [operation, temp_message.copy(), index]
        self.chat_view.children[index].message = message
        await self.chat_view.children[index].reset()
        self.chat_view.children[index].focus()

    async def _append(self, message: dict) -> None:
        self.messages.append(message.copy())
        await self.chat_view.mount(Message(self.chat, self.messages[-1]))
        await self.chat_view.children[-1].finish()
        self.chat_view.scroll_end(animate=False)
        self.chat_view.children[-1].focus(scroll_visible=False)

    async def _remove(self) -> None:
        del self.messages[-1]
        await self.chat_view.children[-1].remove()
        self.chat_view.scroll_end(animate=False)
        if self.chat_view.children:
            self.chat_view.children[-1].focus(scroll_visible=False)

    async def undo(self) -> None:
        if self.undo_index >= 0:
            operation, message, index = self.undo_list[self.undo_index]
            if operation == "remove":
                await self._append(message)
            if operation == "append":
                await self._remove()
            if operation == "change":
                await self._change(operation, message, index)
            self.chat.write_chat_history()
            self.undo_index-=1
            self.chat.refresh_bindings()

    async def redo(self) -> None:
        if self.undo_index < len(self.undo_list)-1:
            self.undo_index+=1
            operation, message, index = self.undo_list[self.undo_index]
            if operation == "remove":
                await self._remove()
            if operation == "append":
                await self._append(message)
            if operation == "change":
                await self._change(operation, message, index)
            self.chat.write_chat_history()
            self.chat.refresh_bindings()

    def append_undo(self, operation: str, message: dict, index: int = -1) -> None:
        while len(self.undo_list)-1 > self.undo_index:
            del self.undo_list[-1]
        while len(self.undo_list) > 100:
            del self.undo_list[0]
        self.undo_list.append([operation, message.copy(), index])
        self.undo_index=len(self.undo_list)-1
