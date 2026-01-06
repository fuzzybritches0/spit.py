# SPDX-License-Identifier: GPL-2.0
import json
import httpx
from spit_app.helpers import dot2obj
from typing import Generator, Tuple, List, Dict, Any

class LlamaCppEndpoint:
    def __init__(self, messages, endpoint, prompt, tools):
        self.messages = messages
        self.endpoint = endpoint
        self.api_endpoint = self.endpoint["endpoint_url"]["value"] + "/v1/chat/completions"
        self.prompt = prompt
        self.tools = tools
        self.timeout = 15
        self.tc_list = [{}]

    def prepare_payload(self) -> Dict[str, Any]:
        self.reasoning_key = self.endpoint["reasoning_key"]["value"]
        payload = {}
        payload["messages"] = []
        if self.prompt:
            payload["messages"].append({"role": "system", "content": self.prompt})
        for message in self.messages:
            if "reasoning" in message:
                message[self.reasoning_key] = message["reasoning"]
                del message["reasoning"]
            payload["messages"].append(message)
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
        if "id" in content:
            if "id" in self.tc_list[-1] and not content["id"] == self.tc_list[-1]["id"]:
                self.tc_list.append({})
            if not "id" in self.tc_list[-1]:
                self.tc_list[-1]["id"] = content["id"]
        if "type" in content:
            self.tc_list[-1]["type"] = content["type"]
        if self.tc_list[-1]["type"] == "function":
            if not "function" in self.tc_list[-1]:
                self.tc_list[-1]["function"] = {}
            if "name" in content["function"]:
                self.tc_list[-1]["function"]["name"] = content["function"]["name"]
            if "arguments" in content["function"]:
                if not "arguments" in self.tc_list[-1]["function"]:
                    self.tc_list[-1]["function"]["arguments"] = ""
                self.tc_list[-1]["function"]["arguments"] += content["function"]["arguments"]

    def extract_fields(self, delta: Dict[str, Any]) -> Generator[Tuple[str, str], None, None]:
        choice = delta["choices"][0]["delta"]
        if content := choice.get("content"):
            yield "content", content
        elif content := choice.get(self.reasoning_key):
            yield "reasoning", content
        elif content := choice.get("tool_calls"):
            self.tool_calls(content[0])
        elif self.tc_list[0]:
            yield "tool_calls", json.dumps(self.tc_list)
            self.tc_list = [{}]

    async def stream(self) -> Generator[Tuple[str, str], None, None]:
        headers = {}
        api_key = self.endpoint["key"]["value"]
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
