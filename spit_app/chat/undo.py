# SPDX-License-Identifier: GPL-2.0
import spit_app.chat.message as message
import spit_app.chat.render as render

def focus_message(self, index: int) -> None:
    self.query_one("#chat-view").children[index].focus()
    self.focused_message = self.query_one("#chat-view").children[index]

async def undo(self) -> None:
    if self.undo_index >= 0:
        operation, umessage, index = self.undo[self.undo_index]
        if operation == "remove":
            self.messages.append(umessage.copy())
            await render.message(self, umessage)
            focus_message(self, -1)
        if operation == "append":
            del self.messages[-1]
            await message.remove_last_turn(self)
            focus_message(self, -1)
        if operation == "change":
            temp_umessage = self.messages[index].copy()
            self.messages[index] = umessage.copy()
            self.undo[self.undo_index] = [operation, temp_umessage.copy(), index]
            self.edit = True
            self.edit_container = self.query_one("#chat-view").children[index]
            await render.message(self, umessage)
            focus_message(self, index)
            self.edit = False
        self.write_chat_history()
        self.undo_index-=1

async def redo(self) -> None:
    if self.undo_index < len(self.undo)-1:
        self.undo_index+=1
        operation, umessage, index = self.undo[self.undo_index]
        if operation == "remove":
            del self.messages[-1]
            await message.remove_last_turn(self)
            focus_message(self, -1)
        if operation == "append":
            self.messages.append(umessage.copy())
            await render.message(self, umessage)
            focus_message(self, -1)
        if operation == "change":
            temp_umessage = self.messages[index].copy()
            self.messages[index] = umessage.copy()
            self.undo[self.undo_index] = [operation, temp_umessage.copy(), index]
            self.edit = True
            self.edit_container = self.query_one("#chat-view").children[index]
            await render.message(self, umessage)
            focus_message(self, index)
            self.edit = False
        self.write_chat_history()

def append_undo(self, operation: str, umessage: dict, index: int = -1) -> None:
    while len(self.undo)-1 > self.undo_index:
        del self.undo[-1]
    while len(self.undo) > 100:
        del self.undo[0]
    self.undo.append([operation, umessage.copy(), index])
    self.undo_index=len(self.undo)-1
