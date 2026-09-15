# SPDX-License-Identifier: GPL-2.0
from copy import deepcopy
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
        temp_message = deepcopy(self.messages[index])
        self.messages[index] = deepcopy(message)
        self.undo_list[self.undo_index] = [operation, deepcopy(temp_message), index]
        message_widget = self.chat_view.require_widget(index)
        message_widget.message = self.messages[index]
        await message_widget.reset()
        await message_widget.finish()
        message_widget.focus()

    async def _insert(self, message: dict, index: int) -> None:
        if index == len(self.messages):
            self.messages.append(deepcopy(message))
            await self.chat_view.mount(Message(self.chat, self.messages[-1]))
        else:
            self.messages.insert(index, deepcopy(message))
            await self.chat_view.mount(Message(self.chat, self.messages[index]),
                before=self.chat_view.child_position(index))
        inserted = self.chat_view.require_widget(index)
        await inserted.finish()
        inserted.focus()

    async def _remove(self, index: int) -> None:
        del self.messages[index]
        await self.chat_view.require_widget(index).remove()
        if self.chat_view.children:
            # the message that followed took the vacated position; removing the
            # tail leaves the neighbour before it. `widget(index)` is that test
            # now - "is there a mounted widget at this message index" - because a
            # child count answers nothing once either end can be evicted.
            neighbour = self.chat_view.widget(index)
            if neighbour is None:
                neighbour = self.chat_view.require_widget(index - 1)
            neighbour.focus()

    async def undo(self) -> None:
        if self.undo_index >= 0:
            operation, message, index = self.undo_list[self.undo_index]
            if operation == "remove":
                await self._insert(message, index)
            elif operation == "insert":
                await self._remove(index)
            elif operation == "change":
                await self._change(operation, message, index)
            self.chat.write_chat_history()
            self.undo_index-=1
            self.chat.refresh_bindings()

    async def redo(self) -> None:
        if self.undo_index < len(self.undo_list)-1:
            self.undo_index+=1
            operation, message, index = self.undo_list[self.undo_index]
            if operation == "remove":
                await self._remove(index)
            elif operation == "insert":
                await self._insert(message, index)
            elif operation == "change":
                await self._change(operation, message, index)
            self.chat.write_chat_history()
            self.chat.refresh_bindings()

    def append_undo(self, operation: str, message: dict, index: int) -> None:
        while len(self.undo_list)-1 > self.undo_index:
            del self.undo_list[-1]
        while len(self.undo_list) > 100:
            del self.undo_list[0]
        self.undo_list.append([operation, deepcopy(message), index])
        self.undo_index=len(self.undo_list)-1
