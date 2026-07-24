import os
import time
import httpx
import signal
import asyncio
import platform
from pathlib import Path
from copy import deepcopy
from textual.widgets import Select
from .models import MODELS

class HelpersMixIn:
    def gets(self, setting: str, key: str|None = None) -> any:
        if setting in self.settings.llamacpp and self.settings.llamacpp[setting]:
            if key and key in self.settings.llamacpp[setting]:
                return self.settings.llamacpp[setting][key]
            if key:
                return None
            ret = self.settings.llamacpp[setting]
            if "integer" in self.manage[setting]["stype"]:
                return int(ret)
            if "float" in self.manage[setting]["stype"]:
                return float()
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

    def get_llamacpp_file(self, version: int) -> str:
        machine = platform.uname().machine
        if machine == "x86_64":
            machine = "x64"
        elif machine == "aarch64":
            machine = "amd64"
        return f"llama-b{version}-bin-ubuntu-vulkan-{machine}.tar.gz"

    def get_versions(self) -> tuple:
        versions = ()
        for item in os.listdir(self.path["llamacpp"]):
            if os.path.isdir(self.path["llamacpp"] / item):
                version = item[6:]
                versions += ((version, version),)
        return versions

    def get_models_list(self) -> list:
        models = deepcopy(MODELS)
        if self.gets("custom_models"):
            for model_id in self.gets("custom_models").keys():
                models[model_id] = self.gets("custom_models", model_id)
        return models

    def get_models_downloaded(self) -> tuple:
        models = ()
        for model_id in os.listdir(self.path["models"]):
            if os.path.isdir(self.path["models"] / model_id):
                model_name = self.get_model(model_id)["name"]
                models += ((model_name, model_id),)
        return models

    def get_model(self, model_id: str) -> dict:
        models = self.get_models_list()
        if model_id in models:
            return models[model_id]
        return {}

    async def get_vulkan_devices(self, llama_version: str) -> list:
        llama_server = self.path["llamacpp"] / ("llama-" + llama_version) / "llama-server"
        devices = []
        try:
            output = await self.run_get_output([str(llama_server), "--list-devices"])
            for line in output.split("\n"):
                if line.strip().startswith("Vulkan"):
                    devices.append(line.strip().split(":")[0].strip())
            return devices
        except:
            return []
    
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
        while True:
            line_bytes = await proc.stdout.readline()
            if not line_bytes:
                break
            yield line_bytes.decode("UTF-8", errors="replace")
        #stdout, _ = await proc.communicate()
        #for line in stdout.decode("UTF-8", errors="replace").splitlines(keepends=True):
        #    yield line
        return_code = await proc.wait()
        if not return_code == 0:
            self.app.exception = Exception(f"Process failed with exit code: {return_code}!")
        proc = None

    def stop(self, proc) -> None:
        if not proc:
            return None
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except:
            pass
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
