# SPDX-License-Identifier: GPL-2.0
import json
import httpx

async def get_models(endpoint: dict) -> list:
    api_endpoint = endpoint["endpoint_url"]["value"] + "/models"
    async with httpx.AsyncClient(timeout=3) as client:
        response = await client.get(api_endpoint)
    if not response.status_code == 200:
        raise RuntimeError(f"Endpoint returned {resp.status_code}: {resp.text}")
    return json.loads(response.text)["models"]

async def get_models_tuple(endpoint: dict) -> tuple:
    models = []
    try:
        models = await get_models(endpoint)
    except Exception as exception:
        if type(exception).__name__ in ("TimeoutError", "ConnectError", "RuntimeError", "ConnectTimeout"):
            pass
        else:
            raise exception
    options = ()
    for model in models:
        options += ((model["name"], model["name"]),)
    if not options:
        return (("None", "none"),)
    else:
        return options

def dot2obj(data: dict, dotpath: str, value: str|int|float|bool) -> None:
    path = dotpath.split(".")
    cur = data
    for key in path[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            cur[key] = {}
        cur = cur[key]
    cur[path[-1]] = value

class LlamaCppEndpoint:
    def __init__(self, messages: list, endpoint: dict, model: str, model_settings: dict,
                 prompt: str, tools: list, callback: callable = None):
        self.messages = messages
        self.callback = callback
        self.endpoint = endpoint
        self.model = model
        self.model_settings = model_settings
        self.api_endpoint = self.endpoint["endpoint_url"]["value"] + "/chat/completions"
        self.timeout = self.endpoint["timeout"]["value"]
        if self.timeout == 0:
            self.timeout = None
        self.prompt = prompt
        self.tools = tools

    async def maybe_callback(self, signal: int) -> None:
        if self.callback:
            await self.callback(signal)

    def construct_payload(self, payload: dict, settings: dict) -> None:
        for setting in settings.keys():
            value = settings[setting]["value"]
            if (not setting == "name" and not setting == "endpoint_url" and
                not setting == "key" and not setting == "reasoning_key"):
                if "." in setting and (value or value is False):
                    dot2obj(payload, setting, value)
                else:
                    if value or value is False:
                        payload[setting] = value

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
        if self.model:
            payload["model"] = self.model
        self.construct_payload(payload, self.endpoint)
        self.construct_payload(payload, self.model_settings)
        if self.tools:
            payload["tools"] = self.tools
            payload["tool_choice"] = "auto"
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
                    if not line:
                        continue
                    try:
                        delta = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    await self.extract_fields(delta)
        await self.maybe_callback(0)
