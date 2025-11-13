import json
import spit_app.message as message
from spit_app.patterns.pattern_processing import PatternProcessing

def remove_last_message(self) -> None:
    if self.state[-1]:
        del self.state[-1]

def load_chat_history(self):
    try:
        with open(self.config.CHAT_HISTORY_PATH, "r") as f:
            self.state = json.load(f)
    except FileNotFoundError:
        self.state = []

def write_chat_history(self):
    with open(self.config.CHAT_HISTORY_PATH, "w") as f:
        json.dump(self.state, f)

def read_system_prompt(self):
    try:
        with open(self.config.SYSTEM_PROMPT_PATH, "r") as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception as e:
        raise e

def load_state(self):
    load_chat_history(self)
    if not self.state:
        system_prompt = read_system_prompt(self)
        if system_prompt:
            self.state.append({"role": "system", "content": system_prompt})

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
