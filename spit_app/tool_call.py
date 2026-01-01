# SPDX-License-Identifier: GPL-2.0
import os
import sys
import json
import importlib.util
from pathlib import Path

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
        self.tool_descs = []
        file_path = __file__.split("/")
        file_path = "/".join(file_path[:-1]) + "/tools"
        for tool in os.listdir(file_path):
            if tool.endswith(".py"):
                module = load_module_from_path(f"tools.{tool}", file_path + "/" + tool)
                self.tools[tool[:-3]] = getattr(module, "call")
                self.tool_descs.append(getattr(module, "desc"))

    def call(self, tool_call: dict, chat_id: str) -> dict:
        return {"role": "tool",
                "tool_call_id": tool_call["id"],
                "name": tool_call["function"]["name"],
                "content": self.tools[tool_call["function"]["name"]](self.app,
                                    json.loads(tool_call["function"]["arguments"]), chat_id)
                }
