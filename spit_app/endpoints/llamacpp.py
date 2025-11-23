# SPDX-License-Identifier: GPL-2.0
from spit_app.helpers.dot2obj import dot2obj
from typing import Generator, Tuple, List, Dict, Any
from .base import BaseEndpoint

class LlamaCppEndpoint(BaseEndpoint):

    @property
    def api_endpoint(self) -> str:
        if "endpoint_url" in self.config.configs[self.active]["values"]:
            return self.config.configs[self.active]["values"]["endpoint_url"] + "/v1/chat/completions"
        return None

    def prepare_payload(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {}
        payload["messages"] = messages
        for setting, value in self.config.configs[self.active]["values"].items():
            if not setting == "name" and not setting == "endpoint_url" and not setting == "key":
                if "." in setting and value:
                    payload = dot2obj(payload, setting, value)
                else:
                    if value:
                        payload[setting] = value
        if self.config.tools:
            payload["tools"] = self.config.tools
            payload["tool_choice"] = "auto"
        payload["n_predict"] = -1
        payload["cache_prompt"] = True
        payload["stream"] = True
        return payload

    def extra_init(self) -> None:
        self.b_tool_calls = False
        self.tid = None
        self.ttype = None
        self.fname = None
        self.ffunction = False
        self.farguments = False

    def tool_calls(self, content: dict) -> Generator[Tuple[str, str], None, None]:
        if not self.b_tool_calls:
            yield 'tool_calls', '['
            self.b_tool_calls = True
        if "id" in content:
            if self.tid and not self.tid == content["id"]:
                yield 'tool_calls', '}},'
                self.resetf()
                self.b_tool_calls = True
            if not self.tid:
                self.tid = content["id"]
                yield 'tool_calls', '{"id":"' + self.tid + '",'
        if "type" in content:
            self.ttype = content["type"]
            yield 'tool_calls', f'"type":"{self.ttype}",'
        if self.ttype == "function":
            if not self.ffunction:
                yield 'tool_calls', '"function":{'
                self.ffunction = True
            if "name" in content["function"]:
                self.fname = content["function"]["name"]
                yield 'tool_calls', f'"name":"{self.fname}",'
            if "arguments" in content["function"]:
                if not self.farguments:
                    yield 'tool_calls', '"arguments":'
                    self.farguments = True
                yield 'tool_calls', content["function"]["arguments"]

    def extract_fields(self, delta: Dict[str, Any]) -> Generator[Tuple[str, str], None, None]:
        choice = delta["choices"][0]["delta"]

        if content := choice.get("content"):
            yield "content", content
        elif content := choice.get("reasoning_content"):
            yield "reasoning_content", content
        elif content := choice.get("tool_calls"):
            for t, c in self.tool_calls(content[0]):
                yield t, c
        else:
            if self.b_tool_calls:
                yield "tool_calls", '}}]'
