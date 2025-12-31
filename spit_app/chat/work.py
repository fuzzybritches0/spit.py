# SPDX-License-Identifier: GPL-2.0
from spit_app.chat.workstream import WorkStream
from spit_app.tools.tool_call import Tool
import spit_app.chat.render as render
import spit_app.chat.message as message
import json

class Work():
    def __init__(self, chat) -> None:
        self.app = chat.app
        self.chat = chat
        self.pp = self.chat.pattern_processing(self.chat)
        self.content = ""
        self.reasoning = ""
        self.tool_calls = ""
        self.was_reasoning = False
        self.display_thinking = False

    def tools(self, buffer: str) -> None:
        self.pp.tool_call = True
        self.tool_calls+=buffer[:1]
        if not self.pp.paragraph.startswith("- TOOL CALL: `"):
            self.pp.paragraph = "- TOOL CALL: `"
        self.pp.paragraph+=buffer[:1]

    def freasoning(self, buffer: str) -> None:
        self.was_reasoning = True
        self.pp.thinking = True
        self.content = ""
        self.pp.paragraph = ""
        if self.pp.skip_buff_c > 0:
            self.pp.skip_buff_c -= 1
        else:
            self.reasoning+=buffer[:1]

    def fcontent(self, buffer: str) -> None:
        if not self.pp.thinking:
            if self.pp.skip_buff_p > 0:
                self.pp.skip_buff_p -= 1
            else:
                self.pp.paragraph += buffer[:1]
            if self.pp.skip_buff_c > 0:
                self.pp.skip_buff_c -= 1
            else:
                self.content += buffer[:1]

    async def buffer(self, buffer: str, ctype: str) -> None:
        if ctype == "content":
            self.pp.thinking = False
        await self.pp.process_patterns(True, buffer)
        if ctype == "reasoning":
            self.freasoning(buffer)
        elif ctype == "content":
            if self.was_reasoning:
                self.pp.thinking = False
            self.fcontent(buffer)
        elif ctype == "tool_calls":
            if self.was_reasoning:
                self.pp.thinking = False
            self.tools(buffer)
        else:
            if self.was_reasoning:
                self.pp.thinking = False
            self.fcontent(buffer)

    async def part(self, part: str) -> None:
        if self.pp.thinking:
            if self.display_thinking is False:
                self.display_thinking = True
                await message.update(self.chat, "Thinking...")
        else:
            await message.update(self.chat, self.pp.paragraph)

    async def stream_response(self):
        self.app.refresh_bindings()
        await message.mount(self.chat, "response", False)
        self.chat_view.focus_message(-1)

        workstream = WorkStream(self.chat)
        async for ctype, buffer, part in workstream.stream(self.chat.messages):
            if buffer:
                await self.buffer(buffer, ctype)
            if part:
                await self.part(part)

        if self.pp.tool_call:
            self.pp.paragraph+="`"
        await message.update(self.chat, self.pp.paragraph)
        if not self.reasoning:
            self.reasoning = None
        if self.tool_calls:
            self.tool_calls = json.loads(self.tool_calls)
            new_tool_calls = []
            for tool_call in self.tool_calls:
                tool_call["function"]["arguments"] = json.dumps(tool_call["function"]["arguments"])
                new_tool_calls.append(tool_call)
        if not self.content:
            self.content = None

        msg = {}
        msg["role"] = "assistant"
        msg["content"] = self.content
        if self.tool_calls:
            msg["tool_calls"] = new_tool_calls
        if self.reasoning:
            msg["reasoning"] = self.reasoning
        self.chat.save_message(msg)
        self.app.refresh_bindings()

async def work_tools(self, tool_calls: list) -> None:
    while tool_calls:
        for tool_call in tool_calls:
            tool = Tool()
            tool_response = tool.call(tool_call)
            self.chat.save_message(tool_response)
            await render.message(self.chat, self.messages[-1])
        work = Work(self)
        await work.stream_response()
        tool_calls = work.tool_calls

async def work_stream(self) -> None:
    if "tool_calls" in self.messages[-1]:
        await work_tools(self, self.messages[-1]["tool_calls"])
    else:
        work = Work(self)
        await work.stream_response()
        await work_tools(self, work.tool_calls)
