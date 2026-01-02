# SPDX-License-Identifier: GPL-2.0
import json
import httpx
from spit_app.helpers import dot2obj
from typing import Generator, Tuple, List, Dict, Any

class LlamaCppEndpoint:
    def __init__(self, messages, endpoint, prompt, tools):
        self.messages = messages
        self.endpoint = endpoint
        self.api_endpoint = self.endpoint["values"]["endpoint_url" ] + "/v1/chat/completions"
        self.prompt = prompt
        self.tools = tools
        self.timeout = 15
        self.b_tool_calls = False
        self.resetf()

    def resetf(self) -> None:
        self.tid = None
        self.ttype = None
        self.fname = None
        self.ffunction = False
        self.farguments = False

    def prepare_payload(self) -> Dict[str, Any]:
        self.reasoning_key = self.endpoint["values"]["reasoning_key"]
        payload = {}
        payload["messages"] = []
        if self.prompt:
            payload["messages"].append({"role": "system", "content": self.prompt})
        for message in self.messages:
            if "reasoning" in message:
                message[self.reasoning_key] = message["reasoning"]
                del message["reasoning"]
            payload["messages"].append(message)
        for setting, value in self.endpoint["values"].items():
            if (not setting == "name" and not setting == "endpoint_url" and
                not setting == "key" and not setting == "reasoning_key"):
                if "." in setting and (value or value is False):
                    dot2obj(payload, setting, value)
                else:
                    if value or value is False:
                        payload[setting] = value
        if self.tools:
            payload["tools"] = self.tools
            payload["tool_choice"] = "auto"
        payload["n_predict"] = -1
        payload["cache_prompt"] = True
        payload["stream"] = True
        return payload

    def tool_calls(self, content: dict) -> Generator[Tuple[str, str], None, None]:
        if not self.b_tool_calls:
            yield 'tool_calls', '['
            self.b_tool_calls = True
        if "id" in content:
            if self.tid and not self.tid == content["id"]:
                yield 'tool_calls', '}},'
                self.resetf()
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
        elif content := choice.get(self.reasoning_key):
            yield "reasoning", content
        elif content := choice.get("tool_calls"):
            for t, c in self.tool_calls(content[0]):
                yield t, c
        else:
            if self.b_tool_calls:
                yield "tool_calls", '}}]'

    async def stream(self) -> Generator[Tuple[str, str], None, None]:
        headers = {}
        api_key = self.endpoint["values"]["key"]
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        headers["Content-Type"] = "application/json"
        payload = self.prepare_payload()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", self.api_endpoint, headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"Endpoint returned {resp.status_code}: {resp.text}")

                async for raw_line in resp.aiter_lines():
                    if not raw_line or not raw_line.startswith("data:"):
                        continue

                    line = raw_line[5:].strip()
                    if not line:
                        continue

                    try:
                        delta = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    for field, value in self.extract_fields(delta):
                        yield field, value
