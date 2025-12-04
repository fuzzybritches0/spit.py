# SPDX-License-Identifier: GPL-2.0
import json
from copy import copy
import spit_app.message as message

def load_chat_history(self):
    try:
        with open(self.settings.CHAT_HISTORY_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def get_mtype(self, role) -> str:
    if role == "user" or role == "tool":
        return "request"
    else:
        return "response"

async def undo(self) -> None:
    if self.undo_index >= 0:
        operation, umessage, index = self.undo[self.undo_index]
        mtype = get_mtype(self, umessage["role"])
        if operation == "remove":
            self.messages.append(copy(umessage))
            await message.render_message(self, mtype, umessage["content"])
        if operation == "append":
            del self.messages[-1]
            await message.remove_last_turn(self)
        if operation == "change":
            temp_message = copy(self.messages[index])
            self.messages[index] = copy(umessage)
            self.undo[self.undo_index] = [operation, copy(temp_message), index]
            self.edit = True
            self.edit_container = self.chat_view.children[index]
            await message.render_message(self, mtype, umessage["content"])
            self.edit = False
        write_chat_history(self)
        self.undo_index-=1

async def redo(self) -> None:
    if self.undo_index < len(self.undo)-1:
        self.undo_index+=1
        operation, umessage, index = self.undo[self.undo_index]
        mtype = get_mtype(self, umessage["role"])
        if operation == "remove":
            del self.messages[-1]
            await message.remove_last_turn(self)
        if operation == "append":
            self.messages.append(copy(umessage))
            await message.render_message(self, mtype, umessage["content"])
        if operation == "change":
            temp_message = copy(self.messages[index])
            self.messages[index] = copy(umessage)
            self.undo[self.undo_index] = [operation, copy(temp_message), index]
            self.edit = True
            self.edit_container = self.chat_view.children[index]
            await message.render_message(self, mtype, umessage["content"])
            self.edit = False
        write_chat_history(self)

def append_undo(self, operation: str, message: dict, index: int = -1) -> None:
    while len(self.undo)-1 > self.undo_index:
        del self.undo[-1]
    while len(self.undo) > 100:
        del self.undo[0]
    self.undo.append([operation, copy(message), index])
    self.undo_index=len(self.undo)-1

def save_message(self, message: dict) -> None:
    self.messages.append(message)
    append_undo(self, "append", message)
    write_chat_history(self)

def write_chat_history(self) -> None:
    with open(self.settings.CHAT_HISTORY_PATH, "w") as f:
        json.dump(self.messages, f)

def load_system_prompt(self) -> None:
    try:
        with open(self.settings.SYSTEM_PROMPT_PATH, "r") as f:
            self.system_prompt = f.read()
    except FileNotFoundError:
        self.system_prompt = None
    except Exception as e:
        raise e

def load_messages(self) -> None:
    self.messages = load_chat_history(self)
    self.code_listings = []
    self.latex_listings = []
    self.undo = []
    self.undo_index=-1
