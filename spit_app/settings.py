# SPDX-License-Identifier: GPL-2.0
from platformdirs import user_config_dir, user_data_dir
from pathlib import Path
from copy import deepcopy
from .llamacpp.models import MODELS_SETTINGS

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
        self.path["endpointsf"] = self.path["data"] / "endpoints.json"
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
        self.save_prompts()

    def save_endpoints(self) -> None:
        self.app.write_json("endpointsf", self.endpoints)

    def save_models(self) -> None:
        models = deepcopy(self.models)
        deletes = []
        for model_id in models.keys():
            if model_id in MODELS_SETTINGS:
                model = deepcopy(models[model_id])
                for setting in models[model_id].keys():
                    if (setting in MODELS_SETTINGS[model_id] and
                        models[model_id][setting]["value"] == MODELS_SETTINGS[model_id][setting]["value"]):
                        del model[setting]
                if not model:
                    deletes += [model_id]
                else:
                    models[model_id] = model
        if deletes:
            for delete in deletes:
                del models[delete]
        self.app.write_json("modelsf", models)

    def load_models(self) -> None:
        if self.path["modelsf"].exists():
            self.models = self.app.read_json("modelsf")
        names = []
        for model_id in self.models.keys():
            if "name" in self.models[model_id]:
                names += [self.models[model_id]["name"]["value"]]
        for model_id in MODELS_SETTINGS.keys():
            if not MODELS_SETTINGS[model_id]["name"]["value"] in names:
                if not model_id in self.models:
                    self.models[model_id] = deepcopy(MODELS_SETTINGS[model_id])
                else:
                    model = deepcopy(MODELS_SETTINGS[model_id])
                    for setting in self.models[model_id].keys():
                        model[setting] = self.models[model_id][setting]
                    self.models[model_id] = deepcopy(model)

    def save_prompts(self) -> None:
        self.app.write_json("promptsf", self.prompts)

    def load(self) -> None:
        self.theme = "gruvbox"
        self.endpoints = {}
        self.prompts = {}
        self.models = {}
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
        if self.path["promptsf"].exists():
            self.prompts = self.app.read_json("promptsf")
