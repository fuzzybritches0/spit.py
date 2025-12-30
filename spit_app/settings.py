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
        self.prompts = {}
        self.active_chat = None

    def save(self) -> None:
        settings = {}
        settings["theme"] = self.app.theme
        settings["active_chat"] = self.active_chat
        self.settings_file.write_text(json.dumps(settings))
        self.save_endpoints()
        self.save_prompts()

    def save_endpoints(self) -> None:
        self.endpoints_file.write_text(json.dumps(self.endpoints))

    def save_prompts(self) -> None:
        self.prompts_file.write_text(json.dumps(self.prompts))

    def load(self) -> None:
        self.theme = None
        self.endpoints = {}
        self.prompts = {}
        self.active_chat = None
        if self.settings_file.exists():
            settings = json.loads(self.settings_file.read_text())
            if "theme" in settings:
                self.app.theme = settings["theme"]
            if "active_chat" in settings:
                self.active_chat = settings["active_chat"]
        if self.endpoints_file.exists():
            self.endpoints = json.loads(self.endpoints_file.read_text())
        if self.prompts_file.exists():
            self.prompts = json.loads(self.prompts_file.read_text())
        if not self.endpoints:
            self.init()
        self.tools = self.read_tool_desc()
