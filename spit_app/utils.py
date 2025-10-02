import json
import spit_app.message as message
from spit_app.patterns.pattern_processing import PatternProcessing

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

async def render_messages(self) -> None:
    for msg in self.state:
        if msg["role"] == "user":
            await message.mount(self, "request", "")
            await render_message(self, msg["content"])
        elif msg["role"] == "assistant" and "content" in msg:
            await message.mount(self, "response", "")
            await render_message(self, msg["content"])
    self.chat_view.scroll_end(animate=True)

async def render_message(self, messagec: str) -> None:
    buffer = ""
    pp = PatternProcessing(self)
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
    await message.update(self, pp.paragraph)
