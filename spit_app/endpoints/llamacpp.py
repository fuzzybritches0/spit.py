# SPDX-License-Identifier: GPL-2.0
import json
import httpx
from .helpers import dot2obj

class LlamaCppEndpoint:
    def __init__(self, messages: list, endpoint: dict, prompt: str, tools: list, callback: callable = None):
        self.messages = messages
        self.callback = callback
        self.endpoint = endpoint
        self.api_endpoint = self.endpoint["endpoint_url"]["value"] + "/v1/chat/completions"
        self.timeout = self.endpoint["timeout"]["value"]
        if self.timeout == 0:
            self.timeout = None
        self.prompt = prompt
        self.tools = tools

    async def maybe_callback(self, signal: int) -> None:
        if self.callback:
            await self.callback(signal)

    def prepare_payload(self) -> dict:
        self.reasoning_key = self.endpoint["reasoning_key"]["value"]
        payload = {}
        payload["messages"] = []
        if self.prompt:
            payload["messages"].append({"role": "system", "content": self.prompt})
        for message in self.messages:
            _message = message.copy()
            if "reasoning" in _message:
                reasoning = _message["reasoning"]
                del _message["reasoning"]
                _message[self.reasoning_key] = reasoning
            payload["messages"].append(_message)
        for setting in self.endpoint.keys():
            value = self.endpoint[setting]["value"]
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

    def tool_calls(self, content: dict) -> None:
        if not "tool_calls" in self.messages[-1]:
            self.messages[-1]["tool_calls"] = [{}]
        tc_list = self.messages[-1]["tool_calls"]
        if "id" in content:
            if "id" in tc_list[-1] and not content["id"] == tc_list[-1]["id"]:
                tc_list.append({})
            if not "id" in tc_list[-1]:
                tc_list[-1]["id"] = content["id"]
        if "type" in content:
            tc_list[-1]["type"] = content["type"]
        if tc_list[-1]["type"] == "function":
            if not "function" in tc_list[-1]:
                tc_list[-1]["function"] = {}
            if "name" in content["function"]:
                tc_list[-1]["function"]["name"] = content["function"]["name"]
            if "arguments" in content["function"]:
                if not "arguments" in tc_list[-1]["function"]:
                    tc_list[-1]["function"]["arguments"] = ""
                tc_list[-1]["function"]["arguments"] += content["function"]["arguments"]

    async def extract_fields(self, delta: dict) -> None:
        choice = delta["choices"][0]["delta"]
        if content := choice.get("content"):
            self.messages[-1]["content"] += content
            await self.maybe_callback(2)
        elif content := choice.get(self.reasoning_key):
            self.messages[-1]["reasoning"] += content
            await self.maybe_callback(2)
        elif content := choice.get("tool_calls"):
            self.tool_calls(content[0])
            await self.maybe_callback(2)

    async def stream(self) -> None:
        headers = {}
        api_key = self.endpoint["key"]["value"]
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        headers["Content-Type"] = "application/json"
        payload = self.prepare_payload()
        self.messages.append({"role": "assistant", "reasoning": "", "content": ""})
        await self.maybe_callback(1)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", self.api_endpoint, headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"Endpoint returned {resp.status_code}: {resp.text}")
                async for raw_line in resp.aiter_lines():
                    if not raw_line or not raw_line.startswith("data:"):
                        continue
                    line = raw_line[5:].strip()
                    if line == "[DONE]":
                        await self.maybe_callback(0)
                    elif not line:
                        continue
                    try:
                        delta = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    await self.extract_fields(delta)
