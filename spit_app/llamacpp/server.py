import os
from .helpers import HelpersMixIn
from .llamacpp import MANAGE

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
        self.endpoint = None

    def is_running(self) -> bool:
        if self.server:
            return True
        return False

    def compose_endpoint_settings(self) -> None:
        port = self.gets("server_port")
        timeout = self.gets("timeout")
        cache_prompt = self.gets("cache_prompt")
        self.endpoint = {
            "endpoint_url": {"value": f"http://127.0.0.1:{port}/v1"},
            "key": {"value": self.api_key},
            "timeout": {"value": timeout},
            "reasoning_key": {"value": "reasoning_content"},
            "cache_pompt": {"value": cache_prompt}
        }

    def compose_server_arguments(self) -> list:
        arguments = ["--models-preset", str(self.path["models"] / "models.ini"), "--no-ui",
            "--no-ui-mcp-proxy", "--host", "127.0.0.1", "--port", str(self.gets("server_port")),
            "--api-key", self.api_key]
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
                slist = ""
                for items in value:
                    slist += f"{item},"
                slist = slist[0:-1]
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
                if "draft" in file and not draft:
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

    def server_errors(self) -> None:
        errors = ""
        for line in self.log.split("\n"):
            words = line.split(" ")
            if len(words) > 1:
                if words[1] == "E":
                    errors += f"{' '.join(words[3:])}\n"
        return errors

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
        self.compose_endpoint_settings()
        self.write_preset()
        cmd = [str(llamacpp)]
        cmd += self.compose_server_arguments()
        self.app.action_notify(f"Starting Llama.cpp Server Version {self.gets('active_version')}...")
        async for line in self.run(cmd, "server"):
            self.log += line
        self.app.action_notify(f"Stopped Llama.cpp Server Version {self.gets('active_version')}.")
        if not self.server:
            return None
        if not self.server.returncode == 0:
            server_errors = self.server_errors()
            self.app.exception= Exception(server_errors)
        self.server = None
        self.log = ""

    async def stop(self) -> None:
        self.log = ""
        if self.server:
            await self.terminate(self.server)
            self.server = None
