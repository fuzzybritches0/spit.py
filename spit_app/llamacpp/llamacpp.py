import os
import asyncio
import platform
from textual import work
from .helpers import get_latest_llamacpp_version, get_vulkan_devices
from spit_app.manage.validation import ValidationMixIn
from .handlers import HandlersMixIn
from .buttons import ButtonsMixIn
from .callbacks import CallbacksMixIn
from spit_app.manage.input_widget import InputWidget
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Label, Button, Select, Rule
from .models import MODELS

class Llamacpp(CallbacksMixIn, HandlersMixIn, ButtonsMixIn, ValidationMixIn, VerticalScroll):
    def __init__(self) -> None:
        super().__init__()
        self.id = "manage-llamacpp"
        self.classes = "manage"
        self.manage = {
            "active_version": {"stype": "select", "desc": "Active Version", "ameth": "get_versions"},
            "active_model": {"stype": "select", "desc": "Load Single Model", "ameth": "get_models_downloaded"},
            "content_length": {"stype": "uinteger", "empty": False, "desc": "Content Length (0 = model default)"},
            "server_arguments": {"stype": "string", "desc": "Server Arguments", "empty": True},
            "vulkan_devices": {"stype": "select_list", "desc": "Use Vulkan devices", "options": []},
            "llamacpp_version":{"stype": "string", "empty": False, "desc": "Llama.cpp Version"},
            "delete_version": {"stype": "select", "desc": "Version", "ameth": "get_versions"},
            "download_model": {"stype": "select", "desc": "Manage Models", "ameth": "get_models_select"},
            "name": {"stype": "string", "empty": False, "desc": "Model Name"},
            "org": {"stype": "string", "empty": False, "desc": "Organisation (huggingface.co)"},
            "model": {"stype": "string", "empty": False, "desc": "Model Identifier (huggingface.co)"},
            "files": {"stype": "string", "empty": False, "desc": "Files (.gguf)"},
            "custom_models": {"stype": "dict"},
            "downloads": {"stype": "select_list"}
        }
        self.settings = self.app.settings
        self.path = self.app.settings.path
        self.focused_widget = None

    def valid_setting_files(self, value: str) -> tuple:
        for file in value.split(","):
            file = file.strip()
            if not file.endswith(".gguf"):
                return (False, "Files must end in .gguf!")
        return (True, None)

    def gets(self, setting: str, key: str|None = None) -> any:
        if setting in self.settings.llamacpp and self.settings.llamacpp[setting]:
            if key and key in self.settings.llamacpp[setting]:
                return self.settings.llamacpp[setting][key]
            if key:
                return None
            return self.settings.llamacpp[setting]
        else:
            if self.manage[setting]["stype"] == "select":
                return None
            if self.manage[setting]["stype"] == "select_list":
                return []
            if self.manage[setting]["stype"] == "boolean":
                return False
            if self.manage[setting]["stype"] == "uinteger":
                return "0"
            if self.manage[setting]["stype"] == "string":
                return ""
            if self.manage[setting]["stype"] == "dict":
                return {}

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
        self.settings.llamacpp[setting] = value

    def dels(self, setting: str, key: str|int) -> None:
        del self.settings.llamacpp[setting][key]

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

    def del_downloads_size(self, file_list: list) -> None:
        count = 0
        for file in self.gets("downloads"):
            if file["path"] in file_list:
                self.dels("downloads", count)
            count += 1

    def get_models_list(self) -> list:
        models = MODELS
        if self.gets("custom_models"):
            models += self.gets("custom_models")
        return models

    def get_model(self, model_id: str) -> dict:
        for model in self.get_models_list():
            if model["id"] == model_id:
                return model

    def get_models_select(self) -> tuple:
        models = ()
        for model in MODELS:
            models += ((model["name"], model["id"]),)
        for model in self.gets("custom_models"):
            models += ((model["name"], model["id"]),)
        return models

    def get_models_downloaded(self) -> tuple:
        models = ()
        for model in os.listdir(self.path["models"]):
            if os.path.isdir(self.path["models"] / model):
                model = self.get_model(model)
                models += ((model["name"], model["id"]),)
        return models

    async def edit_manage_screen(self) -> None:
        input_widget = InputWidget(self, self.manage, self.validators)
        await self.mount(Label("Manage llama.cpp server settings:\n"))
        for item in ["active_version", "active_model", "content_length", "server_arguments", "vulkan_devices"]:
            await self.mount_all(await input_widget.setting(item, self.gets(item)))
        await self.mount(Button("Apply", id="apply-llamacpp-settings"))
        await self.mount(Rule())
        await self.mount(Label("Manage llama.cpp server installations:\n"))
        await self.mount_all(await input_widget.setting("llamacpp_version"))
        await self.mount(Button("Download", id="update-llamacpp"))
        await self.mount_all(await input_widget.setting("delete_version"))
        await self.mount(Button("Delete", id="delete-llamacpp"))
        await self.mount(Rule())
        await self.mount_all(await input_widget.setting("download_model"))
        horizontal = Horizontal(classes="auto-height")
        await self.mount(horizontal)
        await horizontal.mount(Button("Download", id="download-model"))
        await horizontal.mount(Button("Delete", id="delete-model"))
        await self.mount(Rule())
        await self.mount(Label("Add custom llama.cpp model:\n"))
        for item in ["name", "org", "model", "files"]:
            await self.mount_all(await input_widget.setting(item))
        await self.mount(Button("Add", id="add-custom-model"))

    def add_devices(self, devices: list) -> tuple:
        tup = ()
        vulkan_devices = []
        if "vulkan_devices" in self.settings.llamacpp:
            vulkan_devices = self.settings.llamacpp["vulkan_devices"]
        for device in devices:
            tup += ((device, device, device in vulkan_devices),)
        return tup

    async def update_input_vulkan_devices(self) -> None:
        async with self.batch():
            self.query_one("#vulkan_devices").display = False
            self.query_one("#label-vulkan_devices").display = False
            if "active_version" in self.settings.llamacpp and self.settings.llamacpp["active_version"]:
                llamacpp = self.path["llamacpp"] / ("llama-" + self.settings.llamacpp["active_version"])
                devices = await get_vulkan_devices(llamacpp)
                if devices:
                    self.query_one("#vulkan_devices").display = True
                    self.query_one("#label-vulkan_devices").display = True
                    self.query_one("#vulkan_devices").clear_options()
                    self.query_one("#vulkan_devices").add_options(self.add_devices(devices))
                else:
                    if "vulkan_devices" in self.settings.llamacpp:
                        del self.settings.llamacpp["vulkan_devices"]
                self.settings.save()

    async def update_input_llamacpp_version(self) -> None:
        latest_version = await get_latest_llamacpp_version(self.settings)
        if latest_version <= 0:
            latest_version = 0
        self.query_one("#llamacpp_version").value = "b" + str(latest_version)

    @work(exclusive=True, exit_on_error=False)
    async def work_update_input_llamacpp_version(self) -> None:
        while True:
            await self.update_input_llamacpp_version()
            await asyncio.sleep(600)

    def update_options(self) -> None:
        options = self.get_versions()
        self.query_one("#active_version").set_options(options)
        self.query_one("#delete_version").set_options(options)

    def ensure_is_highlighted(self) -> None:
        side_panel = self.app.query_one("#side-panel")
        side_panel.can_focus = False
        index = side_panel.get_option_index(self.id)
        side_panel.highlighted = index
