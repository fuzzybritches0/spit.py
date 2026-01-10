# SPDX-License-Identifier: GPL-2.0
from typing import Iterable, Generator, Tuple, List, Dict,Optional
from spit_app.endpoints.llamacpp import LlamaCppEndpoint

class WorkStream:
    def __init__(self, chat) -> None:
        self.chat = chat
        self.buffer = ""
        self.buffer_size_max = 8
        self.parts: List[str] = []
        self.ctypes: List[str] = []
        endpoint = chat.settings.endpoints[chat.chat_endpoint]
        tools_descs = self._tools_descs()
        prompt = self._prompt()
        if prompt:
            prompt = "\n# FUNCTION CALLING INSTRUCTIONS\n\n" + prompt
        if chat.chat_prompt:
            prompt = chat.settings.prompts[chat.chat_prompt]["text"]["value"] + "\n\n# INSTRUCTIONS\n" + prompt
        self.endpoint = LlamaCppEndpoint(chat.messages, endpoint, prompt, tools_descs)

    def _tools_descs(self) -> list:
        tools_descs = []
        for tool in self.chat.app.tool_call.tools.keys():
            tools_descs.append(self.chat.app.tool_call.tools[tool]["desc"])
        return tools_descs

    def _prompt_inst(self, tool) -> str:
        prompt = ""
        if "prompt_inst" in self.chat.app.tool_call.tools[tool]:
            prompt = self.chat.app.tool_call.tools[tool]["prompt_inst"]
            for setting in self.chat.app.tool_call.tools[tool]["settings"].keys():
                value = self.chat.app.tool_call.tools[tool]["settings"][setting]["value"]
                if tool in self.chat.settings.tool_settings:
                    if setting in self.chat.settings.tool_settings[tool]:
                        value = self.chat.settings.tool_settings[tool][setting]["value"]
                prompt = prompt.replace(f"[{setting}]", str(value))
        return prompt

    def _prompt(self) -> str:
        prompt = ""
        for tool in self.chat.app.tool_call.tools.keys():
            tool_prompt = self.chat.app.tool_call.tools[tool]["settings"]["prompt"]["value"]
            if tool in self.chat.settings.tool_settings:
                if "prompt" in self.chat.settings.tool_settings[tool]:
                    tool_prompt = self.chat.settings.tool_settings[tool]["prompt"]["value"]
            prompt += f"- {tool}\n" + tool_prompt
            prompt += self._prompt_inst(tool)
        return prompt

    async def stream(self, messages: List[Dict[str, str]]
               ) -> Generator[Tuple[str, Optional[str], Optional[str]], None, None]:
        async for _ctype, part in self.endpoint.stream():
            self.parts.append(part)
            self.ctypes.append(_ctype)
            for char in part:
                self.buffer+=char
                if (len(self.buffer) < self.buffer_size_max or 
                    self.parts and len(self.buffer) < len(self.parts[0])):
                    continue
                if self.parts and self.buffer.startswith(self.parts[0]):
                    yield self.ctypes[0], None, self.parts[0]
                    del self.parts[0]
                    ctype = self.ctypes[0]
                    del self.ctypes[0]
                yield ctype, self.buffer, None
                self.buffer=self.buffer[1:]
    
        for char in self.buffer:
            if self.parts and self.buffer.startswith(self.parts[0]):
                yield self.ctypes[0], None, self.parts[0]
                del self.parts[0]
                ctype = self.ctypes[0]
                del self.ctypes[0]
            yield ctype, self.buffer, None
            self.buffer=self.buffer[1:]
