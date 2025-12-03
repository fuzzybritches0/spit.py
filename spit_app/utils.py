# SPDX-License-Identifier: GPL-2.0
import json
from copy import copy
import spit_app.message as message
from spit_app.patterns.pattern_processing import PatternProcessing

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
        operation, message, index = self.undo[self.undo_index]
        if operation == "remove":
            self.messages.append(copy(message))
        if operation == "append":
            del self.messages[-1]
        if operation == "change":
            temp_message = copy(self.messages[index])
            self.messages[index] = copy(message)
            self.undo[self.undo_index] = [operation, copy(temp_message), index]
        write_chat_history(self)
        self.undo_index-=1
        await self.chat_view.remove_children()
        await render_messages(self)

async def redo(self) -> None:
    if self.undo_index < len(self.undo)-1:
        self.undo_index+=1
        operation, message, index = self.undo[self.undo_index]
        if operation == "remove":
            del self.messages[-1]
        if operation == "append":
            self.messages.append(copy(message))
        if operation == "change":
            temp_message = copy(self.messages[index])
            self.messages[index] = copy(message)
            self.undo[self.undo_index] = [operation, copy(temp_message), index]
        write_chat_history(self)
        await self.chat_view.remove_children()
        await render_messages(self)

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

def read_system_prompt(self) -> str | None:
    try:
        with open(self.settings.SYSTEM_PROMPT_PATH, "r") as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception as e:
        raise e

def load_messages(self) -> None:
    self.messages = load_chat_history(self)
    self.code_listings = []
    self.latex_listings = []
    if not self.messages:
        system_prompt = read_system_prompt(self)
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})
    if self.messages[0]["role"] == "system":
        self.code_listings.append([])
        self.latex_listings.append([])
    self.undo = []
    self.undo.append(copy(self.messages))
    self.undo_index=0

async def render_messages(self) -> None:
    for msg in self.messages:
        if msg["role"] == "user" and msg["content"]:
            await render_message(self, "request", msg["content"])
        elif msg["role"] == "assistant" and "content" in msg and msg["content"]:
            await render_message(self, "response", msg["content"])
        elif msg["role"] == "assistant" and "tool_calls" in msg and msg["tool_calls"]:
            for tool_call in msg["tool_calls"]:
                await render_message(self, "response", "- TOOL CALL: `" + json.dumps(tool_call) + "`")
        elif msg["role"] == "tool" and "content" in msg and msg["content"]:
            await render_message(self, "request", "- RESULT: `" + msg["content"] + "`")

async def render_message(self, mtype: str, messagec: str) -> None:
    buffer = ""
    pp = PatternProcessing(self)
    await message.mount(self, mtype)
    for char in messagec:
        buffer += char
        if len(buffer) < 8:
            continue
        await pp.process_patterns(False, buffer)
        if pp.skip_buff_p > 0:
            pp.skip_buff_p -= 1
        else:
            pp.paragraph += buffer[:1]
        buffer = buffer[1:]

    for char in buffer:
        await pp.process_patterns(False, buffer)
        if pp.skip_buff_p > 0:
            pp.skip_buff_p -= 1
        else:
            pp.paragraph += buffer[:1]
        buffer = buffer[1:]
    if not pp.paragraph:
        await message.remove(self)
    else:
        await message.update(self, pp.paragraph)
