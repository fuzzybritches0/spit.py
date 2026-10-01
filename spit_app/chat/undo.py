# SPDX-License-Identifier: GPL-2.0
from copy import deepcopy

class Undo:
    def __init__(self, chat) -> None:
        self.chat = chat
        self.chat_view = chat.chat_view
        self.app = chat.app
        self.messages = chat.messages
        self.undo_list = []
        self.undo_index = -1

    # Each primitive changes the DATA and then brings the widget tree along. The
    # widget tree is the whole history (`children[i] is messages[i]`), so after
    # the data half the child at the same index is the widget to rebuild - no
    # lookup, no window, no gap. `write_chat_history()` persists the data, and
    # it is the UNDO caller (`undo()`/`redo()` below) that writes once per
    # replayed operation.

    async def _change(self, operation: str,message: dict, index: int) -> None:
        temp_message = deepcopy(self.messages[index])
        self.messages[index] = deepcopy(message)
        self.undo_list[self.undo_index] = [operation, deepcopy(temp_message), index]
        self.chat_view.children[index].message = self.messages[index]
        await self.chat_view.children[index].reset()
        await self.chat_view.children[index].finish()
        self.chat_view.children[index].focus()

    async def _insert(self, message: dict, index: int) -> None:
        if index == len(self.messages):
            self.messages.append(deepcopy(message))
        else:
            self.messages.insert(index, deepcopy(message))
        # The dict is in the data BEFORE the widget is asked for, which is
        # `mount_message`'s precondition: it mounts at the neighbour's position
        # and hands back the widget itself, so `finish()` and `focus()` below run
        # on the message this undo inserted and not on whatever sits at the
        # index afterwards.
        inserted = await self.chat_view.mount_message(index)
        await inserted.finish()
        inserted.focus()

    async def _remove(self, index: int) -> None:
        child = self.chat_view.children[index]
        async with child.lock:
            await child.remove()
        del self.messages[index]
        # The vacated position: the message that followed took it, so the
        # neighbour that answers is `children[index]`, or the one before it when
        # the tail went, or the text area when the chat is empty. The ONE rule
        # `remove_message_at` uses too, so the two removal paths cannot disagree
        # about where the cursor goes.
        self.chat_view.focus_after_removal(index)

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
