# SPDX-License-Identifier: GPL-2.0
from spit_app.endpoints.llamacpp import LlamaCppEndpoint

class Work:
    def __init__(self, chat) -> None:
        self.chat = chat
        self.app = chat.app
        self.settings = chat.app.settings
        self.messages = self.chat.messages
        tools_descs = self.tools_descs()
        prompt = self.prompt()
        endpoint = self.settings.endpoints[chat.chat_endpoint]
        self.endpoint = LlamaCppEndpoint(self.messages, endpoint, prompt, tools_descs, self.chat.callback)

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
            tool_prompt = self.app.tool_call.tools[tool]["settings"]["prompt"]["value"]
            if tool in self.settings.tool_settings:
                if "prompt" in self.settings.tool_settings[tool]:
                    tool_prompt = self.settings.tool_settings[tool]["prompt"]["value"]
            prompt += f"- {tool}\n" + tool_prompt
            prompt += self.prompt_inst(tool)
        if prompt:
            prompt = "\n# FUNCTION CALLING INSTRUCTIONS\n\n" + prompt
        if self.chat.chat_prompt:
            chat_prompt = self.settings.prompts[self.chat.chat_prompt]["text"]["value"]
            prompt =  chat_prompt + "\n\n# INSTRUCTIONS\n" + prompt
        return prompt

    async def work_stream(self) -> None:
        if "tool_calls" in self.messages[-1]:
            for tool_call in self.messages[-1]["tool_calls"]:
                await self.app.tool_call.call(self.messages, tool_call, self.chat.id)
                await self.chat.chat_view.mount_message(self.messages[-1])
                self.chat.write_chat_history()
        await self.endpoint.stream()
        if "tool_calls" in self.messages[-1]:
            await self.work_stream()
            self.chat.write_chat_history()
