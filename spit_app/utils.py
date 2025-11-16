# SPDX-License-Identifier: GPL-2.0
import json
import copy
import spit_app.message as message
from spit_app.patterns.pattern_processing import PatternProcessing

def load_chat_history(self):
    try:
        with open(self.config.CHAT_HISTORY_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

async def state_undo(self) -> None:
    if self.undo_index > 0:
        self.undo_index-=1
        self.state = copy.deepcopy(self.undo[self.undo_index])
        await self.chat_view.remove_children()
        await render_messages(self)

async def state_redo(self) -> None:
    if self.undo_index < len(self.undo)-1:
        self.undo_index+=1
        self.state = copy.deepcopy(self.undo[self.undo_index])
        await self.chat_view.remove_children()
        await render_messages(self)

def append_undo_state(self) -> None:
    while len(self.undo)-1 > self.undo_index:
        del self.undo[-1]
    while len(self.undo) > 100:
        del self.undo[0]
    self.undo.append(copy.deepcopy(self.state))
    self.undo_index=len(self.undo)-1

def save_message(self, message: dict) -> None:
    self.state.append(message)
    append_undo_state(self)
    write_chat_history(self)

def write_chat_history(self) -> None:
    with open(self.config.CHAT_HISTORY_PATH, "w") as f:
        json.dump(self.state, f)

def read_system_prompt(self) -> str | None:
    try:
        with open(self.config.SYSTEM_PROMPT_PATH, "r") as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception as e:
        raise e

def load_state(self) -> None:
    self.state = load_chat_history(self)
    if not self.state:
        system_prompt = read_system_prompt(self)
        if system_prompt:
            self.state.append({"role": "system", "content": system_prompt})
    self.undo = []
    self.undo.append(copy.deepcopy(self.state))
    self.undo_index=0

async def render_messages(self, from_index: int = 0) -> None:
    for msg in self.state[from_index:]:
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
