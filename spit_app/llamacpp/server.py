import os
import json
import httpx
from .helpers import HelpersMixIn
from .llamacpp import MANAGE

IGNORE_ERRORS = [
    "operator(): http client error: Connection handling canceled"
]

class Server(HelpersMixIn):
    def __init__(self, app) -> None:
        self.manage = MANAGE
        self.settings = app.settings
        self.path = app.path
        self.api_key = app.get_rand_seq(32)
        self.app = app
        self.preset = ""
        self.log = ""
        self.server = None
        self.active_models = []
        self.model_load_progress = 0
        self.current_cache_id = None
        self.name = "Spit.py Local Server"
        self.ignore_errors = IGNORE_ERRORS

    async def model_action(self, model: str, action: str) -> bool:
        endpoint = f"http://127.0.0.1:{self.gets('server_port')}/models/{action}"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        json = {"model": f"{model}"}
        try:
            async with httpx.AsyncClient(timeout=720) as client:
                response = await client.post(endpoint, headers=headers, json=json)
        except:
            return False
        if response.status_code == 200:
            if action == "unload":
                del self.active_models[self.active_models.index(model)]
            return True
        else:
            if action == "load" and self.app.load_progress_bar_screen:
                await self.app.load_progress_bar_screen.dismiss()
            self.app.exception = Exception(response.text)
        return False

    async def cache_action(self, cache_id: str, action: str) -> bool:
        model = self.app.query_one("#main").query_one(f"#{cache_id}").cs("model")
        endpoint = f"http://127.0.0.1:{self.gets('server_port')}/slots/0?action={action}"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        json = {"filename": f"{cache_id}", "model": model}
        try:
            async with httpx.AsyncClient(timeout=720) as client:
                response = await client.post(endpoint, headers=headers, json=json)
        except:
            return False
        if response.status_code == 200:
            return True
        return False

    def is_running(self) -> bool:
        if self.server:
            return True
        return False

    @property
    def endpoint(self) -> None:
        return {
            "name": { "value": self.name, "stype": "string"},
            "endpoint_url": {"value": f"http://127.0.0.1:{self.gets('server_port')}/v1", "stype": "string"},
            "key": {"value": self.api_key, "stype": "string"},
            "timeout": {"value": self.gets("timeout"), "stype": "uinteger"},
            "reasoning_key": {"value": "reasoning_content", "stype": "string"},
            "cache_prompt": {"value": self.gets("cache_prompt"), "stype": "boolean"}
        }

    def compose_server_arguments(self) -> list:
        arguments = ["--models-preset", str(self.path["models"] / "models.ini"), "--no-ui",
            "--no-ui-mcp-proxy", "--host", "127.0.0.1", "--port", str(self.gets("server_port")),
            "--api-key", self.api_key, "--slot-save-path", str(self.path["prompt_cache"]),
            "--slots", "--parallel", "1", "--offline"]
        devices = ""
        if self.gets("vulkan_devices"):
            for device in self.gets("vulkan_devices"):
                devices += f"{device},"
        if devices:
            devices = devices[0:-1]
            arguments += ["--device", devices]
        else:
            arguments += ["--device", "none"]
        return arguments

    def conc(self, line: str, clear: bool = False) -> None:
        if clear:
            self.preset = ""
        self.preset += f"{line}\n"

    def compose_model_server_settings(self, model_id: str) -> None:
        settings = self.gets("server_settings", model_id)
        for setting in settings.keys():
            stype = settings[setting]["stype"]
            value = settings[setting]["value"]
            if stype == "select_list":
                slist = ",".join(value)
                self.conc(f"{setting} = {slist}")
            elif stype == "boolean":
                if value:
                    value = "true"
                else:
                    value = "false"
                self.conc(f"{setting} = {value}")
            else:
                value = str(value)
                self.conc(f"{setting} = {value}")

    def compose_preset(self) -> None:
        self.conc("version = 1", True)
        for model_id in self.gets("active_models"):
            model_config = self.get_model(model_id)
            model_setting = self.gets("server_settings", model_id)
            model = None
            draft = None
            mmproj = None
            for file in model_config["files"]:
                if ("draft" in file or "mtp" in file) and not draft:
                    draft = file
                elif "mmproj" in file and not mmproj:
                    mmproj = file
                elif not model:
                    model = file
            if not model:
                continue
            self.conc(f"[{model_config['name']}]")
            if model:
                model_file = str(self.path["models"] / model_id / model)
                self.conc(f"model = {model_file}")
            if draft:
                draft_file = str(self.path["models"] / model_id / draft)
                self.conc(f"model-draft = {draft_file}")
            if mmproj:
                mmproj_file = str(self.path["models"] / model_id / mmproj)
                self.conc(f"mmproj = {mmproj_file}")
            self.compose_model_server_settings(model_id)

    def write_preset(self) -> None:
        self.compose_preset()
        with open(self.path["models"] / "models.ini", "w") as file:
            file.write(self.preset)

    def server_error(self, line) -> None:
        words = line.split(" ")
        if len(words) > 2:
            if words[1] == "E" or words[2] == "E":
                error = " ".join(words[3:]).strip()
                if not error in self.ignore_errors:
                    self.app.exception= Exception(error)

    def model_loading_progress(self, line) -> None:
        mark = "cmd_child_to_router:state:"
        line = line.split(" ", 1)[-1]
        if not line.startswith(mark):
            return None
        line = line[len(mark)-1:][1:-1]
        try:
            state = json.loads(line)
        except:
            return None
        if "state" in state and "payload" in state:
            if state["state"] == "ready" and "id" in state["payload"]:
                self.active_models.append(state["payload"]["id"])
                self.model_load_progress = 0
            elif (state["state"] == "loading" and "stages" in state["payload"]
                  and "value" in state["payload"] and "current" in state["payload"]):
                stages = state["payload"]["stages"]
                value = round(state["payload"]["value"] * 100) / len(stages)
                current = stages.index(state["payload"]["current"])
                self.model_load_progress = round((100 / len(stages) * current) + value)

    def start(self) -> None:
        self.app.run_worker(self.start_work())

    async def start_work(self) -> None:
        if not self.gets("active_version") or not self.gets("active_models"):
            return None
        llamacpp = self.path["llamacpp"] / ("llama-" + self.gets("active_version")) / "llama-server"
        if not os.path.isfile(llamacpp):
            self.puts("active_version", None)
            self.settings.save()
            return None
        self.write_preset()
        cmd = [str(llamacpp)]
        cmd += self.compose_server_arguments()
        self.app.action_notify(f"Starting Llama.cpp Server Version {self.gets('active_version')}...")
        async for line in self.run(cmd, "server"):
            self.model_loading_progress(line)
            self.server_error(line)
            self.log += line
        self.app.action_notify(f"Stopped Llama.cpp Server Version {self.gets('active_version')}.")
        self.server = None
        self.log = ""

    async def stop(self) -> None:
        self.log = ""
        if self.server:
            await self.terminate(self.server)
            self.server = None

    async def stop_kill(self) -> None:
        self.log = ""
        if self.server:
            await self.kill(self.server)
            self.server = None
