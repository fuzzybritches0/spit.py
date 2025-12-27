# SPDX-License-Identifier: GPL-2.0
from typing import Iterable, Generator, Tuple, List, Dict,Optional
from spit_app.endpoints.llamacpp import LlamaCppEndpoint

class WorkStream:
    def __init__(self, app) -> None:
        self.buffer = ""
        self.buffer_size_max = 8
        self.parts: List[str] = []
        self.ctypes: List[str] = []
        endpoint = app.settings.endpoints[app.chat_endpoint]
        if app.chat_prompt:
            prompt = app.settings.prompts[app.chat_prompt]
        else:
            prompt = None
        tools = app.settings.tools
        self.endpoint = LlamaCppEndpoint(app.messages, endpoint, prompt, tools)

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
