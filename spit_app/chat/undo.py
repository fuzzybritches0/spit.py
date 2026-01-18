# SPDX-License-Identifier: GPL-2.0
class Undo:
    def __init__(self, chat) -> None:
        self.chat = chat
        self.chat_view = chat.chat_view
        self.app = chat.app
        self.messages = chat.messages
        self.undo_list = []
        self.undo_index = -1

    async def undo(self) -> None:
        if self.undo_index >= 0:
            operation, message, index = self.undo_list[self.undo_index]
            if operation == "remove":
                self.messages.append(message.copy())
                await self.chat.chat_view.mount_message(self.messages[-1])
                self.chat_view.focus_message(-1)
            if operation == "append":
                del self.messages[-1]
                await self.chat.remove_last_message()
                self.chat_view.focus_message(-1)
            if operation == "change":
                temp_message = self.messages[index].copy()
                self.messages[index] = message.copy()
                self.undo_list[self.undo_index] = [operation, temp_message.copy(), index]
                await self.chat.update_message(index)
                self.chat_view.focus_message(index)
            self.chat.write_chat_history()
            self.undo_index-=1
            self.chat.refresh_bindings()

    async def redo(self) -> None:
        if self.undo_index < len(self.undo_list)-1:
            self.undo_index+=1
            operation, message, index = self.undo_list[self.undo_index]
            if operation == "remove":
                del self.messages[-1]
                await self.chat.remove_last_message()
                self.chat_view.focus_message(-1)
            if operation == "append":
                self.messages.append(message.copy())
                await self.chat.chat_view.mount_message(self.messages[-1])
                self.chat_view.focus_message(-1)
            if operation == "change":
                temp_message = self.messages[index].copy()
                self.messages[index] = message.copy()
                self.undo_list[self.undo_index] = [operation, temp_message.copy(), index]
                await self.chat.update_message(index)
                self.chat_view.focus_message(index)
            self.chat.write_chat_history()
            self.chat.refresh_bindings()

    def append_undo(self, operation: str, message: dict, index: int = -1) -> None:
        while len(self.undo_list)-1 > self.undo_index:
            del self.undo_list[-1]
        while len(self.undo_list) > 100:
            del self.undo_list[0]
        self.undo_list.append([operation, message.copy(), index])
        self.undo_index=len(self.undo_list)-1
