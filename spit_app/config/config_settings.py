# SPDX-License-Identifier: GPL-2.0
from platformdirs import user_config_dir
from pathlib import Path
import json

class ConfigSettings:
    config_path = Path(user_config_dir("spit.py", "fuzzybritches0"))
    config_path.mkdir(parents=True, exist_ok=True)
    config_file = config_path / "settings.json"

    CHAT_HISTORY_PATH = "chat_history.json"
    SYSTEM_PROMPT_PATH = "system_prompt.txt"
    TOOL_DESC_PATH = "tools.json"

    def read_tool_desc(self):
        try:
            with open(self.TOOL_DESC_PATH, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            raise e

    def init(self) -> None:
        self.active_config = 0
        self.configs = []
        self.new()

    def save(self) -> None:
        config = {}
        config["active_config"] = self.active_config
        config["configs"] = self.configs
        self.config_file.write_text(json.dumps(config))

    def store(self, cconfig: int, setting: str, stype: str, value: str | bool) -> None:
        if stype == "Float" and value:
            value = float(value)
        elif stype == "Integer" and value:
            value = int(value)
        self.configs[cconfig]["values"][setting] = value
        
    def load(self) -> None:
        if self.config_file.exists():
            config = json.loads(self.config_file.read_text())
            self.active_config = config["active_config"]
            self.configs = config["configs"]
        else:
            self.init()
        self.tools = self.read_tool_desc()

    def new(self) -> int:
        ccount = len(self.configs)
        self.configs.append(
            {
                "values": {
                    "name": f"default config {ccount}",
                    "endpoint_url": "http://127.0.0.1:8080",
                    "key": None
                },
                "custom": [
                    ("name", "String", "Name", []),
                    ("endpoint_url", "String", "Endpoint URL", []),
                    ("key", "String", "API Access Key", []),
                    ("temperature", "Float", "Temperature", []),
                    ("top_p", "Float", "TOP-P", []),
                    ("min_p", "Float", "MIN-P", []),
                    ("top_k", "Float", "TOP-K", [])
                ]
            }
        )
        return ccount

    def set_active(self, conf: int) -> None:
        self.active_config = conf
        self.save()

    def delete_config(self, conf: int) -> None:
        active = self.active_config
        del self.configs[conf]
        if active == conf:
            self.active_config = 0
        if len(self.configs) < 1:
            self.init()
        self.save()

    def remove_custom_setting(self, conf: int, rsetting: str) -> None:
        custom = []
        values = {}
        for setting, stype, desc, sarray in self.configs[conf]["custom"]:
            if not rsetting == setting:
                custom.append((setting, stype, desc, sarray))
                if setting in self.configs[conf]["values"]:
                    values[setting] = self.configs[conf]["values"][setting]
        self.configs[conf]["custom"] = custom
        self.configs[conf]["values"] = values

    def add_custom_setting(self, conf: int, setting: str, stype: str, desc: str, sarray: list) -> None:
        self.configs[conf]["custom"].append((setting, stype, desc, sarray))
