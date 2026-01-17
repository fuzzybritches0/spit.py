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
                self.tools[name]["call"] = getattr(module, "call")
                if hasattr(module, "PROMPT_INST"):
                    self.tools[name]["prompt_inst"] = getattr(module, "PROMPT_INST")

    async def call(self, messages: dict, tool_call: dict, chat_id: str) -> None:
        name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])
        if inspect.iscoroutinefunction(self.tools[name]["call"]):
            result = await self.tools[name]["call"](self.app, arguments, chat_id)
            messages.append({"role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_call["function"]["name"],
                    "content": result
                    })
        elif inspect.isfunction(self.tools[name]["call"]):
            result = self.tools[name]["call"](self.app, arguments, chat_id)
            messages.append({"role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_call["function"]["name"],
                    "content": result
                    })
