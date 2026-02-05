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

class ToolCall:
    def __init__(self, app) -> None:
        self.app = app
        self.tools = {}
        file_path = __file__.split("/")
        file_path = "/".join(file_path[:-1]) + "/tools"
        for tool in os.listdir(file_path):
            if tool.endswith(".py"):
                name = tool[:-3]
                self.tools[name] = {}
                module = load_module_from_path(f"tools.{tool}", file_path + "/" + tool)
                self.tools[name]["desc"] = getattr(module, "DESC")
                self.tools[name]["settings"] = getattr(module, "SETTINGS")
                if hasattr(module, "call"):
                    self.tools[name]["call"] = getattr(module, "call")
                else:
                    self.tools[name]["call_async_generator"] = getattr(module, "call_async_generator")
                if hasattr(module, "PROMPT_INST"):
                    self.tools[name]["prompt_inst"] = getattr(module, "PROMPT_INST")
                if hasattr(module, "Validators"):
                    self.tools[name]["validators"] = getattr(module, "Validators")

    def required_arguments(self, name: str, arguments: dict) -> None|str:
        for argument in self.tools[name]["desc"]["function"]["parameters"]["required"]:
            if not argument in arguments:
                return f"ERROR: missing argument: {argument}! Function call failed!"
        return None

    async def maybe_callback(self, signal: int) -> None:
        if self.callback:
            await self.callback(signal)

    async def call(self, messages: list, tool_call: dict, chat_id: str, callback: callable = None) -> None:
        self.callback = callback
        chat = self.app.query_one("#main").query_one(f"#{chat_id}")
        chat_view = chat.chat_view
        name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])
        messages.append({"role": "tool", "tool_call_id": tool_call["id"],
                "name": name, "content": ""})
        await self.maybe_callback(1)
        if not name in chat.chat_tools or not name in self.tools.keys():
            messages[-1]["content"] = f"ERROR: tool {name} not available!"
            await self.maybe_callback(2)
            await self.maybe_callback(0)
            return None
        missing = self.required_arguments(name, arguments)
        if missing:
            messages[-1]["content"] = missing
            await self.maybe_callback(2)
            await self.maybe_callback(0)
            return None
        if "call" in self.tools[name]:
            if inspect.iscoroutinefunction(self.tools[name]["call"]):
                messages[-1]["content"] += await self.tools[name]["call"](self.app, arguments, chat_id)
            elif inspect.isfunction(self.tools[name]["call"]):
                messages[-1]["content"] += self.tools[name]["call"](self.app, arguments, chat_id)
            await self.maybe_callback(2)
        else:
            async for chunk in self.tools[name]["call_async_generator"](self.app, arguments, chat_id):
                messages[-1]["content"] += chunk
                await self.maybe_callback(2)
        await self.maybe_callback(0)
