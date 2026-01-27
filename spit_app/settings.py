# SPDX-License-Identifier: GPL-2.0
from platformdirs import user_config_dir, user_data_dir
from pathlib import Path
from uuid import uuid4

class Settings:
    def __init__(self, app) -> None:
        self.app = app
        self.path = {}
        self.path["data"] = Path(user_data_dir(self.app.NAME, self.app.COPYRIGHT))
        self.path["data"].mkdir(parents=True, exist_ok=True)
        self.path["promptsf"] = self.path["data"] / "prompts.json"
        self.path["endpointsf"] = self.path["data"] / "endpoints.json"
        self.path["settings"] = Path(user_config_dir(self.app.NAME, self.app.COPYRIGHT))
        self.path["settings"].mkdir(parents=True, exist_ok=True)
        self.path["settingsf"] = self.path["settings"] / "settings.json"
        self.path["sandbox"] = self.path["data"] / "sandbox"
        self.path["sandbox"].mkdir(parents=True, exist_ok=True)
        self.path["cache"] = self.path["data"] / "cache"
        self.path["cache"].mkdir(parents=True, exist_ok=True)
        self.path["chats"] = self.path["data"] / "chat"
        self.path["chats"].mkdir(parents=True, exist_ok=True)
        self.path["chats_archive"] = self.path["data"] / "archive"
        self.path["chats_archive"].mkdir(parents=True, exist_ok=True)

    def init(self) -> None:
        self.endpoints = {}
        self.prompts = {}
        self.tool_settings = {}
        self.active_chat = None

    def save(self) -> None:
        settings = {}
        settings["theme"] = self.app.theme
        settings["active_chat"] = self.active_chat
        settings["tool_settings"] = self.tool_settings
        self.app.write_json("settingsf", settings)
        self.save_endpoints()
        self.save_prompts()

    def save_endpoints(self) -> None:
        self.app.write_json("endpointsf", self.endpoints)

    def save_prompts(self) -> None:
        self.app.write_json("promptsf", self.prompts)

    def load(self) -> None:
        self.theme = None
        self.endpoints = {}
        self.prompts = {}
        self.tool_settings = {}
        self.active_chat = None
        if self.path["settingsf"].exists():
            settings = self.app.read_json("settingsf")
            if "theme" in settings:
                self.app.theme = settings["theme"]
            if "active_chat" in settings:
                self.active_chat = settings["active_chat"]
            if "tool_settings" in settings:
                self.tool_settings = settings["tool_settings"]
        if self.path["endpointsf"].exists():
            self.endpoints = self.app.read_json("endpointsf")
        if self.path["promptsf"].exists():
            self.prompts = self.app.read_json("promptsf")
