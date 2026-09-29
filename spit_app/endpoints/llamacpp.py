# SPDX-License-Identifier: GPL-2.0
import json
import httpx
from copy import deepcopy

async def get_models(endpoint: dict) -> list:
    api_endpoint = endpoint["endpoint_url"]["value"] + "/models"
    headers = auth_headers(endpoint)
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(api_endpoint, headers=headers)
    except:
        return []
    if response.status_code == 200:
        try:
            jsonresp = json.loads(response.text)
            if "models" in jsonresp:
                return jsonresp["models"]
            elif "data" in jsonresp:
                return jsonresp["data"]
            else:
                return []
        except:
            return []
    return []

def auth_headers(endpoint: dict) -> dict:
    headers = {}
    if "key" in endpoint and endpoint["key"]["value"]:
        headers["Authorization"] = f"Bearer {endpoint['key']['value']}"
    return headers

def native_address(endpoint: dict) -> str:
    # The OpenAI-compatible endpoints are <server>/v1/...; llama.cpp's own routes
    # (/props, /slots) hang off the server itself, so the trailing /v1 comes off -
    # only when it is there, so an URL without it is not cut into something else.
    url = endpoint["endpoint_url"]["value"]
    if url.endswith("/v1"):
        return url[:-3]
    return url

async def get_json(url: str, headers: dict, params: dict = None) -> dict|list|None:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(url, headers=headers, params=params)
    except:
        return None
    if not response.status_code == 200:
        return None
    try:
        return json.loads(response.text)
    except:
        return None

def n_ctx_of(obj) -> int|None:
    if isinstance(obj, dict) and isinstance(obj.get("n_ctx"), int) and obj["n_ctx"] > 0:
        return obj["n_ctx"]
    return None

async def get_context_size(endpoint: dict, model: str = None) -> int|None:
    # How large the window the server runs is. None means unknown and the caller
    # shows a dash: a guessed limit is a lie about when a chat overflows.
    # Chain: /props (the one answer llama.cpp gives for the model it has loaded -
    # ?model=<id> picks it out of a router/multi-model server), then the first
    # /slots entry that reports one, then the endpoint's own override, then None.
    headers = auth_headers(endpoint)
    address = native_address(endpoint)
    params = {"model": model} if model else None
    props = await get_json(f"{address}/props", headers, params)
    settings = props.get("default_generation_settings") if isinstance(props, dict) else None
    n_ctx = n_ctx_of(settings)
    if n_ctx:
        return n_ctx
    slots = await get_json(f"{address}/slots", headers)
    if isinstance(slots, list):
        for slot in slots:
            n_ctx = n_ctx_of(slot)
            if n_ctx:
                return n_ctx
    override = endpoint.get("context_size")
    value = override.get("value") if isinstance(override, dict) else None
    if isinstance(value, int) and value > 0:
        return value
    return None

class EndpointFailure(Exception):
    # The typed failure of ONE attempt at the endpoint. It carries the two facts
    # the work loop needs and the bare RuntimeError carried neither: `status_code`,
    # what the server answered (None when there was no answer at all, because the
    # request never completed), and `retryable`, whether asking again could possibly
    # change the answer. The classification lives HERE, at the one place that knows
    # what an HTTP status means, so `work.py` can decide on a flag instead of
    # comparing `type(exception).__name__` against a list of names.
    status_code = None
    retryable = False

    def __init__(self, message: str, status_code: int = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class TransientFailure(EndpointFailure):
    # The server was not able to answer THIS time and might answer the next: the
    # transport died, or it said 429/5xx. Asking again is the remedy.
    retryable = True


class ConnectionFailure(TransientFailure):
    # No answer at all - refused, timed out, hung up mid-stream. `status_code` is
    # None because no status was ever received; the retry rule does not need one.
    pass


class StreamFailure(TransientFailure):
    # The request was accepted and the stream then reported an `error` payload and
    # stopped. The answer arrived, so there is a status when the payload carries
    # one; the attempt itself is still worth repeating.
    pass


class DeterministicFailure(EndpointFailure):
    # The server refused this exact payload and will refuse it every time: the 4xx
    # family except 429. Retrying it buys the same refusal three times over and the
    # latency of all three - the reason this hierarchy exists at all.
    pass


class ContextLengthExceeded(DeterministicFailure):
    # The one refusal the app itself cannot answer for: the conversation no longer
    # fits the window. Named because it is the failure the token-status notes try to
    # warn about, and the case where "prompt too long" arriving as a plain 400 IS
    # the first signal on an endpoint that answers neither /props nor /slots.
    pass


CONTEXT_REFUSALS = ("context length", "context_length", "context size", "context window",
                    "maximum context", "max tokens", "too many tokens", "reduce the length")


def is_context_refusal(text: str) -> bool:
    lowered = str(text).lower()
    return any(marker in lowered for marker in CONTEXT_REFUSALS)


def setting_value(endpoint: dict, setting: str, default):
    # An endpoint setting read FOR THE APP rather than for the wire. The saved shape
    # is {"value": ...}; a field emptied in the settings screen keeps the key and
    # leaves value None, and a field saved before it existed is absent at all. All
    # three, and a hand-edited non-number, answer the default.
    entry = endpoint.get(setting)
    value = entry.get("value") if isinstance(entry, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return value


def status_of(code) -> int|None:
    if isinstance(code, bool) or not isinstance(code, int):
        return None
    return code


def refusal_failure(status_code: int, text: str) -> EndpointFailure:
    # The wording is the one the app has always shown the user and the suite pins
    # (`Endpoint returned {code}: {text}`) - the typing adds the two attributes, it
    # does not reword the error.
    message = f"Endpoint returned {status_code}: {text}"
    if is_context_refusal(text):
        return ContextLengthExceeded(message, status_code)
    if status_code == 429 or status_code >= 500:
        return TransientFailure(message, status_code)
    return DeterministicFailure(message, status_code)


def stream_failure(code, typ, message: str) -> EndpointFailure:
    text = f"Endpoint raised Error: {code}, Type: {typ}, {message}"
    if is_context_refusal(f"{code} {typ} {message}"):
        return ContextLengthExceeded(text, status_of(code))
    return StreamFailure(text, status_of(code))


def transport_failure(error: Exception) -> EndpointFailure:
    return ConnectionFailure(f"Endpoint request failed: {type(error).__name__}: {error}")


def nameid(model: dict) -> str:
    if "name" in model:
        return "name"
    return "id"

def get_models_list(models: list) -> list:
    options = []
    for model in models:
        name = nameid(model)
        options += [model[name]]
    return options

def get_models_tuple(models: list) -> tuple:
    options = ()
    for model in models:
        name = nameid(model)
        options += ((model[name], model[name]),)
    if not options:
        return (("None", "none"),)
    else:
        return options

def get_model_capabilities(models: list, _model: str) -> list:
    for model in models:
        name = nameid(model)
        if model[name] == _model:
            if "capabilities" in model:
                return model["capabilities"]
            elif "architecture" in model and "input_modalities" in model["architecture"]:
                return model["architecture"]["input_modalities"]
    return []

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
        # The retry rule is a fact about the ENDPOINT, like the timeout above and
        # `context_size` (DECISIONS 84 a). Read with .get() and a default, so an
        # endpoint saved before these fields existed - every endpoint saved so far -
        # asks for the default instead of raising KeyError: the settings file is
        # read verbatim and no migration was authorised.
        self.attempts = setting_value(self.endpoint, "retry_attempts", 3)
        self.delay = setting_value(self.endpoint, "retry_delay", 1.0)
        self.prompt = prompt
        self.tools = tools
        self.usage = None

    def maybe_callback(self, signal: int) -> None:
        if self.callback:
            self.callback(self.message_index, signal)

    def construct_payload(self, payload: dict, settings: dict) -> None:
        for setting in settings.keys():
            value = settings[setting]["value"]
            # context_size is a client-side fact about the endpoint, not an inference
            # parameter: forwarding it would make the server reject the request.
            if not setting in ["name", "endpoint_url", "key", "reasoning_key", "save_cache_prompt",
                               "parallel", "context_size", "retry_attempts", "retry_delay"]:
                if "." in setting and (value or value is False):
                    dot2obj(payload, setting, value)
                else:
                    if value or value is False or value == 0:
                        if setting == "parallel" and value == 0:
                            value = "auto"
                        if settings[setting]["stype"] == "select_list":
                            payload[setting] = ",".join(value)
                        else:
                            payload[setting] = value

    def prepare_payload(self) -> dict:
        payload = {}
        payload["model"] = self.model
        self.reasoning_key = self.endpoint["reasoning_key"]["value"]
        payload["messages"] = []
        if self.prompt:
            payload["messages"].append({"role": "system", "content": self.prompt})
        for message in self.messages:
            _message = deepcopy(message)
            notes = _message.pop("system", [])
            if "reasoning" in _message:
                reasoning = _message["reasoning"]
                del _message["reasoning"]
                _message[self.reasoning_key] = reasoning
            payload["messages"].append(_message)
            for note in notes:
                self.append_note(payload["messages"], _message, note)
        self.construct_payload(payload, self.endpoint)
        self.construct_payload(payload, self.model_settings)
        if self.tools:
            payload["tools"] = self.tools
            payload["tool_choice"] = "auto"
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
        return payload

    def append_note(self, out: list, carrier: dict, note: dict) -> None:
        # A stored note (the private "system" key a hook wrote into the message dict)
        # rides the wire as `user`, never `system`: strict templates raise_exception
        # on a mid-conversation `system` (P13 hazard 1, owner ruling 2026-09-25).
        # A `user` CARRIER merges instead of appending: that swaps the strictness
        # for the alternation family's own rule (mistral-instruct, gemma-it raise
        # on two consecutive `user` messages), so the note joins the carrier's
        # content rather than becoming the second half of that pair. The deepcopy
        # is what this edits; the stored message keeps its note and its content.
        if carrier["role"] == "user":
            self.merge_into_content(carrier, note["text"])
            return
        out.append({"role": "user", "content": note["text"]})

    def merge_into_content(self, carrier: dict, text: str) -> None:
        content = carrier.get("content")
        if isinstance(content, list):
            for part in reversed(content):
                if part.get("type") == "text":
                    part["text"] = f"{part['text']}\n\n{text}" if part["text"] else text
                    return
            content.append({"type": "text", "text": text})
            return
        carrier["content"] = f"{content}\n\n{text}" if content else text

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

    def extract_fields(self, delta: dict) -> None:
        # A usage chunk carries "choices": [] (OpenAI and llama.cpp since PR #15444),
        # so touching choices[0] before reading it is an IndexError that would kill
        # the stream: work_stream() re-raises everything outside the timeout family.
        choices = delta.get("choices")
        if not choices:
            return
        choice = choices[0]["delta"]
        if content := choice.get("content"):
            self.messages[-1]["content"][0]["text"] += content
            self.maybe_callback(2)
        elif content := choice.get(self.reasoning_key):
            self.messages[-1]["reasoning"] += content
            self.maybe_callback(2)
        elif content := choice.get("tool_calls"):
            self.tool_calls(content[0])
            self.maybe_callback(2)

    def maybe_error(self, delta) -> None:
        if "error" in delta and delta["error"]:
            code = delta["error"].get("code", "unknown")
            message = delta["error"].get("message", "Unknown error occurred.")
            typ = delta["error"].get("type", "unknown")
            raise stream_failure(code, typ, message)

    async def stream_request(self, client, headers: dict, payload: dict) -> tuple|None:
        async with client.stream("POST", self.api_endpoint, headers=headers, json=payload) as resp:
            if not resp.status_code == 200:
                await resp.aread()
                return (resp.status_code, resp.text)
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
                self.maybe_error(delta)
                # read the usage before anything touches choices: old llama.cpp puts
                # it on the finish_reason chunk, new llama.cpp and OpenAI on a final
                # chunk with "choices": [] - one rule covers all three stream shapes.
                if usage := delta.get("usage"):
                    self.usage = usage
                self.extract_fields(delta)
        return None

    async def stream(self) -> None:
        headers = {}
        api_key = self.endpoint["key"]["value"]
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        headers["Content-Type"] = "application/json"
        self.usage = None
        payload = self.prepare_payload()
        self.messages.append({"role": "assistant", "reasoning": "", "content": [{"type": "text", "text": ""}]})
        self.message_index = len(self.messages) - 1
        self.maybe_callback(1)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                refusal = await self.stream_request(client, headers, payload)
                if refusal and 400 <= refusal[0] < 500 and "stream_options" in payload:
                    # A server that refuses the request outright may be refusing the
                    # unknown stream_options field. Token counts are never worth losing
                    # a reply over (old llama.cpp sends the usage unconditionally), so
                    # ask once more without it.
                    del payload["stream_options"]
                    refusal = await self.stream_request(client, headers, payload)
                if refusal:
                    raise refusal_failure(refusal[0], refusal[1])
        except httpx.TransportError as error:
            # The transport set that used to reach `work.py` as five different
            # httpx classes it recognised by NAME: ConnectError, ConnectTimeout,
            # ReadError, ReadTimeout, RemoteProtocolError and the rest of
            # TransportError. They are transient by nature - there was no answer -
            # so they leave here as ONE type carrying retryable, with the httpx
            # error kept as `__cause__` so the user still reads what really
            # happened. CancelledError is not a TransportError and is deliberately
            # not caught: an abort must stop reaching the stream at all.
            raise transport_failure(error) from error
        self.maybe_callback(0)
