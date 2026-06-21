# SPDX-License-Identifier: GPL-2.0
import os
import sys
import json
import asyncio
import inspect
import importlib.util
from pathlib import Path

def load_user_settings(app, name: str, settings: dict) -> None:
    if name in app.settings.tool_settings:
        for setting in app.settings.tool_settings[name].keys():
            settings[setting]["value"] = app.settings.tool_settings[name][setting]["value"]

def load_module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def load_tools(tools: dict, file_path: str) -> None:
    for tool in os.listdir(file_path):
        if tool.endswith(".py"):
            name = tool[:-3]
            tools[name] = {}
            module = load_module_from_path(f"tools.{tool}", file_path + "/" + tool)
            tools[name]["desc"] = getattr(module, "DESC")
            tools[name]["settings"] = getattr(module, "SETTINGS")
            if hasattr(module, "call"):
                tools[name]["call"] = getattr(module, "call")
            else:
                tools[name]["call_async_generator"] = getattr(module, "call_async_generator")
            if hasattr(module, "PROMPT_INST"):
                tools[name]["prompt_inst"] = getattr(module, "PROMPT_INST")
            if hasattr(module, "Validators"):
                tools[name]["validators"] = getattr(module, "Validators")
            tools[name]["requires_multimodal_image"] = False
            if hasattr(module, "REQUIRES_MULTIMODAL_IMAGE"):
                tools[name]["requires_multimodal_image"] = getattr(module, "REQUIRES_MULTIMODAL_IMAGE")
            tools[name]["stream_tool_response"] = False
            if hasattr(module, "STREAM_TOOL_RESPONSE"):
                tools[name]["stream_tool_response"] = getattr(module, "STREAM_TOOL_RESPONSE")

class ToolCall:
    def __init__(self, app) -> None:
        self.app = app
        self.tools = {}
        file_path = __file__.split("/")
        file_path = "/".join(file_path[:-1]) + "/tools"
        load_tools(self.tools, file_path)
        load_tools(self.tools, str(app.settings.path["custom_tools"]))

    def required_arguments(self, name: str, arguments: dict) -> None|str:
        for argument in self.tools[name]["desc"]["function"]["parameters"]["required"]:
            if not argument in arguments:
                return f"ERROR: missing argument: {argument}! Function call failed!"
        return None

    def maybe_callback(self, signal: int) -> None:
        if self.callback:
            self.callback(self.message_index, signal)

    def end_call(self, messages: list, message: str) -> None:
        messages[-1]["content"][0]["text"] = message
        self.maybe_callback(0)
        return None

    async def call_async_generator(self, messages: list, chat_id: str, name: str, arguments) -> None:
        async for chunk in self.tools[name]["call_async_generator"](self.app, arguments, chat_id):
            if chunk:
                messages[-1]["content"][0]["text"] += chunk
                if self.tools[name]["stream_tool_response"]:
                    self.maybe_callback(2)

    def call(self, messages: list, tool_call: dict, chat_id: str, callback: callable = None) -> None:
        self.callback = callback
        chat = self.app.query_one("#main").query_one(f"#{chat_id}")
        chat_view = chat.chat_view
        name = tool_call["function"]["name"]
        messages.append({"role": "tool", "tool_call_id": tool_call["id"],
            "name": name, "content": [{"type": "text", "text": ""}]})
        self.message_index = len(messages) - 1
        self.maybe_callback(1)
        try:
            arguments = json.loads(tool_call["function"]["arguments"])
        except Exception as exception:
            args = tool_call["function"]["arguments"]
            exc = f"{type(exception).__name__}: {exception}"
            message = f"Received tool call `{name}` with invalid JSON: \n~~~~\n{args}\n~~~~\n"
            tool_call["function"]["arguments"] = "{\"noop\":\"noop\"}"
            tool_call["function"]["name"] = "noop"
            return self.end_call(messages, exc + "\n\n" + message)
        if name == "noop":
            return self.end_call(messages, f"INFO: Offending tool call replaced by NOOP!")
        if not name in chat.chat_tools or not name in self.tools.keys():
            return self.end_call(messages, f"ERROR: tool {name} not available!")
        if (self.app.tool_call.tools[name]["requires_multimodal_image"] and
            not "multimodal" in chat.model_capabilities):
            return self.end_call(messages, f"ERROR: tool {name} requires multimodal capabilities!")
        missing = self.required_arguments(name, arguments)
        if missing:
            return self.end_call(messages, missing)
        try:
            if "call" in self.tools[name]:
                if inspect.iscoroutinefunction(self.tools[name]["call"]):
                    ret = asyncio.run(self.tools[name]["call"](self.app, arguments, chat_id))
                    if ret:
                        messages[-1]["content"][0]["text"] += ret
                elif inspect.isfunction(self.tools[name]["call"]):
                    ret = self.tools[name]["call"](self.app, arguments, chat_id)
                    if ret:
                        messages[-1]["content"][0]["text"] += ret
            elif "call_async_generator" in self.tools[name]:
                asyncio.run(self.call_async_generator(messages, chat_id, name, arguments))
            else:
                messages[-1]["content"][0]["text"] = f"ERROR: no function for {name} defined!"
        except Exception as exception:
            messages[-1]["content"][0]["text"] += f"{type(exception).__name__}: {exception}"
        finally:
            self.maybe_callback(0)
