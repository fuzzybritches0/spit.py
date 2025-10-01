from platformdirs import user_config_dir, site_config_dir
from pathlib import Path
import json

class ConfigSettings:
    config_path = Path(user_config_dir("spit.py", "fuzzybritches0"))
    config_path.mkdir(parents=True, exist_ok=True)
    config_file = config_path / "settings.json"

    CHAT_HISTORY_PATH = "chat_history.json"
    SYSTEM_PROMPT_PATH = "system_prompt.txt"

    def init(self) -> None:
        self.config = { "active_config": 0, "configs": [] }
        self.config["configs"].append({ "api": {"name": "default config 0"}, "options": {} })

    def save(self) -> None:
        self.config_file.write_text(json.dumps(self.config))

    def store(self, cconfig: int, slot: str, setting: str, stype: int | float | str, value: str) -> None:
        if (value.lower() == "none" or value.lower() == "default" or value == ""):
            value = None
        elif stype == float:
            value = float(value)
        elif stype == int:
            value = int(value)
        self.config["configs"][cconfig][slot][setting] = value
        
    def load(self) -> None:
        if self.config_file.exists():
            self.config = json.loads(self.config_file.read_text())
        else:
            self.init()

    def new(self) -> int:
        ccount = len(self.config["configs"])
        self.config["configs"].append({ "api": {"name": f"default config {ccount}"}, "options": {} })
        return ccount

    def set_active(self, conf: int) -> None:
        self.config["active_config"] = conf
        self.save()

    def delete_config(self, conf: int) -> None:
        active = self.config["active_config"]
        del self.config["configs"][conf]
        if active == conf:
            self.config["active_config"] = 0
        if len(self.config["configs"]) < 1:
            self.init()
        self.save()
