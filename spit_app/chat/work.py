# SPDX-Liicense-Identifier: GPL-2.0
import asyncio
from spit_app.endpoints.llamacpp import LlamaCppEndpoint

TOOL_PROMPT = "# FUNCTION CALLING INSTRUCTIONS\n\nAll of your function calls are rendered in human-readable form for the user to inspect. The user is also informed about the function call results and can see the tool response message. DO NOT REPEAT THEM!\n\n"

class Work:
    def __init__(self, chat) -> None:
        self.chat = chat
        self.chat_view = chat.chat_view
        self.app = chat.app
        self.settings = chat.app.settings
        self.messages = chat.messages
        tools_descs = self.tools_descs()
        prompt = self.prompt()
        endpoint = self.settings.endpoints[chat.chat_endpoint]
        chat_tools_descs = []
        for tool in tools_descs:
            if tool["function"]["name"] in chat.chat_tools:
                chat_tools_descs.append(tool)
        self.endpoint = LlamaCppEndpoint(self.messages, endpoint, prompt,
                                         chat_tools_descs, self.chat_view.callback)

    def tools_descs(self) -> list:
        tools_descs = []
        for tool in self.app.tool_call.tools.keys():
            tools_descs.append(self.app.tool_call.tools[tool]["desc"])
        return tools_descs

    def prompt_inst(self, tool) -> str:
        prompt = ""
        if "prompt_inst" in self.app.tool_call.tools[tool]:
            prompt = self.app.tool_call.tools[tool]["prompt_inst"]
            for setting in self.app.tool_call.tools[tool]["settings"].keys():
                value = self.app.tool_call.tools[tool]["settings"][setting]["value"]
                if tool in self.settings.tool_settings:
                    if setting in self.settings.tool_settings[tool]:
                        value = self.settings.tool_settings[tool][setting]["value"]
                prompt = prompt.replace(f"[{setting}]", str(value))
        return prompt

    def prompt(self) -> str:
        prompt = ""
        for tool in self.app.tool_call.tools.keys():
            if tool in self.chat.chat_tools:
                tool_prompt = self.app.tool_call.tools[tool]["settings"]["prompt"]["value"]
                if tool in self.settings.tool_settings:
                    if "prompt" in self.settings.tool_settings[tool]:
                        tool_prompt = self.settings.tool_settings[tool]["prompt"]["value"]
                prompt += f"## {tool}\n\n" + tool_prompt
                prompt += self.prompt_inst(tool)
        if prompt:
            prompt = TOOL_PROMPT + prompt
        if self.chat.chat_prompt:
            chat_prompt = self.settings.prompts[self.chat.chat_prompt]["text"]["value"]
            prompt =  "# INSTRUCTIONS\n\n" + chat_prompt + "\n\n" + prompt
        return prompt

    async def work_stream(self) -> None:
        if "tool_calls" in self.messages[-1]:
            for tool_call in self.messages[-1]["tool_calls"]:
                await self.app.tool_call.call(self.messages, tool_call, self.chat.id, self.chat_view.callback)
        try:
            await self.endpoint.stream()
        except Exception as exception:
            self.app.exception = exception
            del self.messages[-1]
            self.chat_view.children[-1].remove()
        if "tool_calls" in self.messages[-1]:
            await self.work_stream()
