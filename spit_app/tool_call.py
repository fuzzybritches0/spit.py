# SPDX-License-Identifier: GPL-2.0
import os
import sys
import json
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
            if hasattr(module, "REQUIRES_MULTIMODAL_IMAGE"):
                tools[name]["requires_multimodal_image"] = getattr(module, "REQUIRES_MULTIMODAL_IMAGE")
            else:
                tools[name]["requires_multimodal_image"] = False

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

    async def maybe_callback(self, signal: int) -> None:
        if self.callback:
            await self.callback(signal)

    async def end_call(self, messages: list, message: str) -> None:
        messages[-1]["content"][0]["text"] = message
        await self.maybe_callback(2)
        await self.maybe_callback(0)
        return None

    async def call(self, messages: list, tool_call: dict, chat_id: str, callback: callable = None) -> None:
        self.callback = callback
        chat = self.app.query_one("#main").query_one(f"#{chat_id}")
        chat_view = chat.chat_view
        name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])
        messages.append({"role": "tool", "tool_call_id": tool_call["id"],
            "name": name, "content": [{"type": "text", "text": ""}]})
        await self.maybe_callback(1)
        if not name in chat.chat_tools or not name in self.tools.keys():
            return await self.end_call(messages, f"ERROR: tool {name} not available!")
        if (self.app.tool_call.tools[name]["requires_multimodal_image"] and
            not "multimodal" in chat.model_capabilities):
            return await self.end_call(messages, f"ERROR: tool {name} requires multimodal capabilities!")
        missing = self.required_arguments(name, arguments)
        if missing:
            return await self.end_call(messages, missing)
        try:
            if "call" in self.tools[name]:
                if inspect.iscoroutinefunction(self.tools[name]["call"]):
                    ret = await self.tools[name]["call"](self.app, arguments, chat_id)
                    if ret:
                        messages[-1]["content"][0]["text"] += ret
                elif inspect.isfunction(self.tools[name]["call"]):
                    ret = self.tools[name]["call"](self.app, arguments, chat_id)
                    if ret:
                        messages[-1]["content"][0]["text"] += ret
                await self.maybe_callback(2)
            elif "call_async_generator" in self.tools[name]:
                async for chunk in self.tools[name]["call_async_generator"](self.app, arguments, chat_id):
                    if chunk:
                        messages[-1]["content"][0]["text"] += chunk
                    await self.maybe_callback(2)
            else:
                messages[-1]["content"][0]["text"] = f"ERROR: no function for {name} defined!"
                self.maybe_callback(2)
        except Exception as exception:
            messages[-1]["content"][0]["text"] += f"{type(exception).__name__}: {exception}"
        await self.maybe_callback(0)
