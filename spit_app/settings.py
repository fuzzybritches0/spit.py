# SPDX-License-Identifier: GPL-2.0
from platformdirs import user_config_dir, user_data_dir
from pathlib import Path
from copy import deepcopy
from .llamacpp.models import MODELS_SETTINGS, MODELS_SERVER_SETTINGS

class Settings:
    def __init__(self, app) -> None:
        self.app = app
        self.path = {}
        self.path["app_home"] = Path.home() / "spit.py"
        self.path["app_home"].mkdir(parents=True, exist_ok=True)
        self.path["custom_tools"] = self.path["app_home"] / "tools"
        self.path["custom_tools"].mkdir(parents=True, exist_ok=True)
        self.path["sandbox"] = self.path["app_home"] / "sandbox"
        self.path["sandbox"].mkdir(parents=True, exist_ok=True)
        self.path["data"] = Path(user_data_dir(self.app.NAME, self.app.COPYRIGHT))
        self.path["data"].mkdir(parents=True, exist_ok=True)
        self.path["promptsf"] = self.path["data"] / "prompts.json"
        self.path["modelsf"] = self.path["data"] / "models.json"
        self.path["modelsf"] = self.path["data"] / "models.json"
        self.path["serversf"] = self.path["data"] / "servers.json"
        self.path["endpointsf"] = self.path["data"] / "endpoints.json"
        self.path["serversf"] = self.path["data"] / "server_settings.json"
        self.path["settings"] = Path(user_config_dir(self.app.NAME, self.app.COPYRIGHT))
        self.path["settings"].mkdir(parents=True, exist_ok=True)
        self.path["settingsf"] = self.path["settings"] / "settings.json"
        self.path["cache"] = self.path["data"] / "cache"
        self.path["cache"].mkdir(parents=True, exist_ok=True)
        self.path["chats"] = self.path["data"] / "chat"
        self.path["chats"].mkdir(parents=True, exist_ok=True)
        self.path["chats_archive"] = self.path["data"] / "archive"
        self.path["chats_archive"].mkdir(parents=True, exist_ok=True)
        self.path["llamacpp"] = self.path["data"] / "llamacpp"
        self.path["llamacpp"].mkdir(parents=True, exist_ok=True)
        self.path["models"] = self.path["data"] / "models"
        self.path["models"].mkdir(parents=True, exist_ok=True)
        self.path["prompt_cache"] = self.path["data"] / "prompt_cache"
        self.path["prompt_cache"].mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        settings = {}
        settings["theme"] = self.app.theme
        settings["active_chat"] = self.active_chat
        settings["tool_settings"] = self.tool_settings
        settings["llamacpp"] = self.llamacpp
        settings["downloads"] = {"pending": self.app.download.pending, "working": self.app.download.working}
        self.app.write_json("settingsf", settings)
        self.save_endpoints()
        self.save_models()
        self.save_server_settings()
        self.save_prompts()

    def save_endpoints(self) -> None:
        self.app.write_json("endpointsf", self.endpoints)

    def save_server_settings(self) -> None:
        self.save_configs(self.server_settings, MODELS_SERVER_SETTINGS, "serversf")

    def save_models(self) -> None:
        self.save_configs(self.models, MODELS_SETTINGS, "modelsf")

    def save_configs(self, in_configs: dict, builtins: dict, file: str) -> None:
        configs = deepcopy(in_configs)
        deletes = []
        for config_id in configs.keys():
            if config_id in builtins:
                config = deepcopy(configs[config_id])
                for setting in configs[config_id].keys():
                    if (setting in builtins[config_id] and
                        configs[config_id][setting]["value"] == builtins[config_id][setting]["value"]):
                        del config[setting]
                if not config:
                    deletes += [config_id]
                else:
                    configs[config_id] = config
        if deletes:
            for delete in deletes:
                del configs[delete]
        self.app.write_json(file, configs)

    def load_server_settings(self) -> None:
        self.load_configs("server_settings", MODELS_SERVER_SETTINGS, "serversf")

    def load_models(self) -> None:
        self.load_configs("models", MODELS_SETTINGS, "modelsf")

    def load_configs(self, configs: dict, builtins: dict, file: str) -> None:
        if self.path[file].exists():
            in_configs = self.app.read_json(file)
        else:
            in_configs = {}
        names = []
        for config_id in in_configs.keys():
            if "name" in in_configs[config_id]:
                names += [in_configs[config_id]["name"]["value"]]
        for config_id in builtins.keys():
            if not names or not builtins[config_id]["name"]["value"] in names:
                if not config_id in in_configs:
                    in_configs[config_id] = deepcopy(builtins[config_id])
                else:
                    config = deepcopy(builtins[config_id])
                    for setting in in_configs[config_id].keys():
                        config[setting] = in_configs[config_id][setting]
                    in_configs[config_id] = deepcopy(config)
        setattr(self, configs, in_configs)

    def save_prompts(self) -> None:
        self.app.write_json("promptsf", self.prompts)

    def load(self) -> None:
        self.theme = "gruvbox"
        self.endpoints = {}
        self.prompts = {}
        self.models = {}
        self.server_settings = {}
        self.tool_settings = {}
        self.llamacpp = {}
        self.downloads = {}
        self.active_chat = None
        if self.path["settingsf"].exists():
            settings = self.app.read_json("settingsf")
            if "theme" in settings:
                self.app.theme = settings["theme"]
            if "active_chat" in settings:
                self.active_chat = settings["active_chat"]
            if "tool_settings" in settings:
                self.tool_settings = settings["tool_settings"]
            if "llamacpp" in settings:
                self.llamacpp = settings["llamacpp"]
            if "downloads" in settings:
                self.downloads = settings["downloads"]
        if self.path["endpointsf"].exists():
            self.endpoints = self.app.read_json("endpointsf")
        self.load_models()
        self.load_server_settings()
        if self.path["promptsf"].exists():
            self.prompts = self.app.read_json("promptsf")
