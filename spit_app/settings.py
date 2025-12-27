# SPDX-License-Identifier: GPL-2.0
from platformdirs import user_config_dir, user_data_dir
from pathlib import Path
from uuid import uuid4
import json

class Settings:
    TOOL_DESC_PATH = "tools.json"

    def __init__(self, app) -> None:
        self.app = app
        self.data_path = Path(user_data_dir(self.app.NAME, self.app.COPYRIGHT))
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.prompts_file = self.data_path / "prompts.json"
        self.endpoints_file = self.data_path / "endpoints.json"
        self.settings_path = Path(user_config_dir(self.app.NAME, self.app.COPYRIGHT))
        self.settings_path.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.settings_path / "settings.json"

    def read_tool_desc(self):
        try:
            with open(self.TOOL_DESC_PATH, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            raise e

    def init(self) -> None:
        self.endpoints = {}
        self.active_chat = None
        self.active_endpoint = None
        self.new()

    def save(self) -> None:
        settings = {}
        settings["theme"] = self.app.theme
        settings["active_endpoint"] = self.active_endpoint
        settings["active_chat"] = self.active_chat
        self.settings_file.write_text(json.dumps(settings))
        self.endpoints_file.write_text(json.dumps(self.endpoints))

    def save_prompts(self) -> None:
        self.prompts_file.write_text(json.dumps(self.prompts))

    def store(self, cur_endpoint: int, setting: str, stype: str, value: str | bool) -> None:
        if stype == "Float" and value:
            value = float(value)
        elif stype == "Integer" and value:
            value = int(value)
        self.endpoints[cur_endpoint]["values"][setting] = value
        
    def load(self) -> None:
        self.theme = None
        self.endpoints = {}
        self.prompts = {}
        self.active_endpoint = None
        self.active_chat = None
        if self.settings_file.exists():
            settings = json.loads(self.settings_file.read_text())
            if "theme" in settings:
                self.app.theme = settings["theme"]
            if "active_endpoint" in settings:
                self.active_endpoint = settings["active_endpoint"]
            if "active_chat" in settings:
                self.active_chat = settings["active_chat"]
        if self.endpoints_file.exists():
            self.endpoints = json.loads(self.endpoints_file.read_text())
        if self.prompts_file.exists():
            self.prompts = json.loads(self.prompts_file.read_text())
        if not self.endpoints:
            self.init()
        self.tools = self.read_tool_desc()

    def new(self) -> str:
        uuid = str(uuid4())
        self.endpoints[uuid] = {
            "values": {
                "name": uuid,
                "endpoint_url": "http://127.0.0.1:8080",
                "key": None,
                "reasoning_key": "reasoning_content"
            },
            "custom": [
                ("name", "String", "Name", []),
                ("endpoint_url", "String", "Endpoint URL", []),
                ("key", "String", "API Access Key", []),
                ("reasoning_key", "Select_no_default", "Reasoning Key", ["reasoning_content", "reasoning"]),
                ("temperature", "Float", "Temperature", []),
                ("top_p", "Float", "TOP-P", []),
                ("min_p", "Float", "MIN-P", []),
                ("top_k", "Float", "TOP-K", [])
            ]
        }
        return uuid

    def new_prompt(self) -> str:
        uuid = str(uuid4())
        self.prompts[uuid] = {
                "name": uuid,
                "text": "You are a friendly AI assistant."
        }
        return uuid

    def set_active(self, conf: int) -> None:
        self.active_endpoint = conf
        self.save()

    def delete_endpoint(self, conf: str) -> None:
        del self.endpoints[conf]
        if self.active_endpoint == conf:
            self.active_endpoint = None
        if len(self.endpoints) < 1:
            self.init()
        self.save()

    def delete_prompt(self, prompt: str) -> None:
        del self.prompts[prompt]
        self.save_prompts()

    def remove_custom_setting(self, conf: int, rsetting: str) -> None:
        custom = []
        values = {}
        for setting, stype, desc, sarray in self.endpoints[conf]["custom"]:
            if not rsetting == setting:
                custom.append((setting, stype, desc, sarray))
                if setting in self.endpoints[conf]["values"]:
                    values[setting] = self.endpoints[conf]["values"][setting]
        self.endpoints[conf]["custom"] = custom
        self.endpoints[conf]["values"] = values

    def add_custom_setting(self, conf: int, setting: str, stype: str, desc: str, sarray: list) -> None:
        self.endpoints[conf]["custom"].append((setting, stype, desc, sarray))
