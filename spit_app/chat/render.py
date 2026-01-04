# SPDX-License-Identifier: GPL-2.0
import json
import spit_app.chat.message as mmessage

async def messages(self) -> None:
    for umessage in self.messages:
        await message(self, umessage)
    self.chat_view.focus_message(-1, False)

async def message(self, umessage) -> None:
    if umessage["role"] == "user" and umessage["content"]:
        await _message(self, "request", umessage["content"])
    elif umessage["role"] == "assistant" and "content" in umessage and umessage["content"]:
        await _message(self, "response", umessage["content"])
    elif umessage["role"] == "assistant" and "tool_calls" in umessage and umessage["tool_calls"]:
        await _tool_calls(self, umessage["tool_calls"])
    elif umessage["role"] == "tool" and "content" in umessage and umessage["content"]:
        await _tool_response(self, umessage["content"])

async def _tool_calls(self, tool_calls) -> None:
    await _message(self, "response", "- TOOL CALL: `" + json.dumps(tool_calls) + "`")

async def _tool_response(self, tool_response) -> None:
    await _message(self, "request", "- RESULT: `" + json.dumps(tool_response) + "`")

async def _message(self, mtype: str, messagec: str) -> None:
    buffer = ""
    pp = self.pattern_processing(self)
    await mmessage.mount(self, mtype)
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
        await mmessage.remove(self)
    else:
        await mmessage.update(self, pp.paragraph)
