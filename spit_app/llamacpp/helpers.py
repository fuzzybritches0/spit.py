import os
import time
import httpx
import signal
import asyncio
import platform
from pathlib import Path
from copy import deepcopy
from textual.widgets import Select
from .models import MODELS, NEW_MODELS_SERVER_SETTINGS

class HelpersMixIn:
    def gets(self, setting: str, key: str|None = None) -> any:
        if setting in self.settings.llamacpp:
            if key and key in self.settings.llamacpp[setting]:
                return self.settings.llamacpp[setting][key]
            if key:
                return None
            ret = self.settings.llamacpp[setting]
            if setting in self.manage:
                if "integer" in self.manage[setting]["stype"]:
                    return int(ret)
                if "float" in self.manage[setting]["stype"]:
                    return float(ret)
            return ret
        else:
            if "value" in self.manage[setting]:
                return self.manage[setting]["value"]
            if self.manage[setting]["stype"] == "select":
                return None
            if self.manage[setting]["stype"] == "select_list":
                return []
            if self.manage[setting]["stype"] == "boolean":
                return False
            if "integer" in self.manage[setting]["stype"]:
                return 0
            if "float" in self.manage[setting]["stype"]:
                return 0.0
            if self.manage[setting]["stype"] == "string":
                return ""
            if self.manage[setting]["stype"] == "dict":
                return {}

    def inpgets(self, setting: str) -> any:
        if "integer" in self.manage[setting]["stype"] or "float" in self.manage[setting]["stype"]:
            return str(self.gets(setting))
        else:
            return self.gets(setting)

    def puts(self, setting: str, value: any = "__NONE__", value2: any = "__NONE__") -> None:
        if not value2 == "__NONE__":
            self.settings.llamacpp[setting][value] = value2
            return None
        if value == "__NONE__":
            if self.manage[setting]["stype"] == "select_list":
                value = self.query_one(f"#{setting}").selected
            else:
                value = self.query_one(f"#{setting}").value
        if value == Select.NULL:
            value = None
        if "integer" in self.manage[setting]["stype"]:
            value = int(value)
        elif "float" in self.manage[setting]["stype"]:
            value = float(value)
        self.settings.llamacpp[setting] = value

    def dels(self, setting: str, key: str|int|None = None) -> None:
        if key:
            del self.settings.llamacpp[setting][key]
        else:
            del self.settings.llamacpp[setting]

    def settings_changed(self, settings: list) -> bool:
        for setting in settings:
            if self.manage[setting]["stype"] == "select_list":
                if not self.gets(setting) == self.query_one(f"#{setting}").selected:
                    gets = self.gets(setting)
                    query = self.query_one(f"#{setting}").selected
                    return True
            elif self.manage[setting]["stype"] == "boolean":
                if not self.gets(setting) == self.query_one(f"#{setting}").value:
                    return True
            else:
                if not str(self.gets(setting)) == self.query_one(f"#{setting}").value:
                    return True
        return False

    def get_llamacpp_file(self, version: int) -> str:
        machine = platform.uname().machine
        if machine == "x86_64":
            machine = "x64"
        elif machine == "aarch64":
            machine = "amd64"
        return f"llama-b{version}-bin-ubuntu-vulkan-{machine}.tar.gz"

    def get_versions_list(self) -> list:
        versions = []
        for item in os.listdir(self.path["llamacpp"]):
            if os.path.isdir(self.path["llamacpp"] / item):
                versions += [item[6:]]
        return versions

    def get_versions(self) -> tuple:
        versions = ()
        for version in self.get_versions_list():
            versions += ((version, version),)
        return versions

    def get_models_dict(self) -> dict:
        models = deepcopy(MODELS)
        if self.gets("custom_models"):
            for model_id in self.gets("custom_models").keys():
                models[model_id] = self.gets("custom_models", model_id)
        return models

    def model_is_downloaded(self, model_id: str) -> bool:
        if not "downloads" in self.settings.llamacpp:
            return False
        model = self.get_model(model_id)
        if not model:
            return False
        files = model["files"]
        count = 0
        for file in files:
            path = self.path["models"] / model_id / file
            size = os.path.getsize(path)
            for download in self.settings.llamacpp["downloads"]:
                if download["path"] == str(path):
                    count += 1
                    if not download["size"] == size:
                        return False
        if not count == len(files):
            return False
        return True

    def get_models_downloaded(self) -> tuple:
        models = ()
        for model_id in os.listdir(self.path["models"]):
            if os.path.isdir(self.path["models"] / model_id):
                if self.model_is_downloaded(model_id):
                    model_name = self.get_model(model_id)["name"]
                    models += ((model_name, model_id),)
        return models

    def get_model(self, model_id: str) -> dict:
        models = self.get_models_dict()
        if model_id in models:
            return models[model_id]
        return {}

    async def get_vulkan_devices(self, llama_version: str) -> list:
        llama_server = self.path["llamacpp"] / ("llama-" + llama_version) / "llama-server"
        devices = []
        try:
            output = await self.run_get_output([str(llama_server), "--list-devices"])
            for line in output.split("\n"):
                if line.strip() == "Available devices:":
                    continue
                if not line.strip():
                    continue
                if line.strip() == "(none)":
                    return []
                devices.append(line.strip().split(":")[0].strip())
            return devices
        except:
            return []

    def get_server_settings(self, model_id) -> dict:
        if not model_id in self.settings.server_settings:
            return deepcopy(NEW_MODELS_SERVER_SETTINGS)
        else:
            return self.settings.server_settings[model_id]

    async def run_get_output(self, cmd: list) -> str:
        output = ""
        async for line in self.run(cmd):
            output += line
        return output
    
    async def run(self, cmd: list, attr: str|None = None):
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT, start_new_session=True)
        if attr:
            setattr(self, attr, proc)
        async for data in proc.stdout:
            yield data.decode("UTF-8", errors="replace")

    async def terminate(self, proc) -> None:
        if not proc:
            return None
        if not proc.returncode == None:
            proc = None
            return None
        else:
            proc.terminate()
            await proc.wait()
            proc = None
    
    async def kill(self, proc) -> None:
        if not proc:
            return None
        if not proc.returncode == None:
            proc = None
            return None
        else:
            proc.kill()
            await proc.wait()
            proc = None

    async def get_latest_llamacpp_version(self) -> int:
        if "latest" in self.settings.llamacpp and "latest_time" in self.settings.llamacpp:
            if time.time() < self.settings.llamacpp["latest_time"] + 3600:
                return self.settings.llamacpp["latest"]
        url = "https://github.com/ggml-org/llama.cpp/releases/latest"
        async with httpx.AsyncClient(timeout=15) as client:
            async with client.stream("GET", url, follow_redirects=True) as resp:
                if resp.status_code != 200:
                    return -1
                async for line in resp.aiter_lines():
                    if "<title>" in line:
                        line = line.strip()
                        try:
                            version = int(line.split(" ")[1][1:])
                        except:
                            version = 0
                        finally:
                            if not version == 0:
                                self.settings.llamacpp["latest"] = version
                                self.settings.llamacpp["latest_time"] = time.time()
                                self.settings.save()
                            return version
        return -2
