import os
import asyncio
from textual import work
from spit_app.manage.validation import ValidationMixIn
from .handlers import HandlersMixIn
from .buttons import ButtonsMixIn
from .callbacks import CallbacksMixIn
from .helpers import HelpersMixIn
from spit_app.manage.input_widget import InputWidget
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.widgets import Label, Button, Rule, Select

MANAGE = {
    "active_version": {"stype": "select", "desc": "Active Version", "ameth": "get_versions"},
    "active_models": {"stype": "select_list", "desc": "Select active Models", "options": []},
    "server_port": {"stype": "uinteger", "empty": False, "desc": "Server Port", "value": "8080"},
    "timeout": {"stype": "uinteger", "empty": False, "desc": "Server Timeout (0: no timeout)", "value": 0},
    "cache_prompt": {"stype": "boolean", "desc": "Cache Prompt", "value": True},
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

class Llamacpp(CallbacksMixIn, HandlersMixIn, ButtonsMixIn, ValidationMixIn, HelpersMixIn, VerticalScroll):
    def __init__(self) -> None:
        super().__init__()
        self.id = "manage-llamacpp"
        self.classes = "manage"
        self.manage = MANAGE
        self.settings = self.app.settings
        self.path = self.app.settings.path
        self.focused_widget = None

    async def edit_manage_screen(self) -> None:
        input_widget = InputWidget(self, self.manage, self.validators)
        await self.mount(Label("Manage llama.cpp server settings:\n"))
        for item in ["active_version", "active_models", "server_port", "timeout", "cache_prompt",
            "vulkan_devices"]:
            await self.mount_all(await input_widget.setting(item, self.inpgets(item)))
        await self.mount(Button("Apply", id="apply-llamacpp-settings"))
        await self.mount(Rule())
        await self.mount(Label("Manage llama.cpp server installations:\n"))
        await self.mount_all(await input_widget.setting("llamacpp_version"))
        await self.mount(Button("Download", id="update-llamacpp"))
        await self.mount_all(await input_widget.setting("delete_version"))
        await self.mount(Button("Delete", id="delete-llamacpp"))
        await self.mount(Rule())
        await self.mount_all(await input_widget.setting("download_model"))
        await self.mount(Vertical(id="server-settings"))
        horizontal = Horizontal(classes="auto-height")
        await self.mount(horizontal)
        await horizontal.mount(Button("Download", id="download-model"))
        await horizontal.mount(Button("Delete", id="delete-model"))
        await self.mount(Rule())
        await self.mount(Label("Add custom llama.cpp model:\n"))
        for item in ["name", "org", "model", "files"]:
            await self.mount_all(await input_widget.setting(item))
        await self.mount(Button("Add", id="add-custom-model"))

    def valid_setting_server_port(self, value: str) -> tuple:
        try:
            int(value)
        except:
            return (False, "Not a valid port number!")
        if int(value) <= 1000 or int(value) > 65536:
            return (False, "Port number out of range!")
        return(True, None)

    def valid_setting_name(self, value: str) -> tuple:
        for model_id in self.get_models_list().keys():
            if self.get_model(model_id)["name"] == value:
                return (False, "Model name must be unique!")
        return (True, None)

    def valid_setting_llamacpp_version(self, value: str) -> tuple:
        if not value.startswith("b"):
            return (False, "Must start with b...")
        try:
            int(value[1:])
        except:
            return (False, "Must be a valid llama.cpp version!")
        return (True, None)

    def valid_setting_files(self, value: str) -> tuple:
        for file in value.split(","):
            file = file.strip()
            if not file.endswith(".gguf"):
                return (False, "Files must end in .gguf!")
        return (True, None)

    def get_models_select(self) -> tuple:
        models = ()
        for model_id in self.get_models_list().keys():
            models += ((self.get_model(model_id)["name"], model_id),)
        return models

    def models_select_list(self) -> tuple:
        models = ()
        for model in self.get_models_downloaded():
            n, i = model
            if i in self.gets("active_models"):
                models += ((n, i, True),)
            else:
                models += ((n, i, False),)
        return models

    def add_devices(self, devices: list) -> tuple:
        tup = ()
        vulkan_devices = []
        if "vulkan_devices" in self.settings.llamacpp:
            vulkan_devices = self.settings.llamacpp["vulkan_devices"]
        for device in devices:
            tup += ((device, device, device in vulkan_devices),)
        return tup

    def update_models_select_list(self) -> None:
        models = self.models_select_list()
        active_models = self.query_one("#active_models")
        if models:
            active_models.display = True
            self.query_one("#label-active_models").display = True
            active_models.clear_options()
            active_models.add_options(models)
        else:
            active_models.display = False
            self.query_one("#label-active_models").display = False

    async def update_input_vulkan_devices(self) -> None:
        async with self.batch():
            llamacpp = self.query_one("#active_version").value
            vulkan_devices = self.query_one("#vulkan_devices")
            if llamacpp == Select.NULL:
                devices = []
            else:
                devices = await self.get_vulkan_devices(llamacpp)
            if devices:
                vulkan_devices.display = True
                self.query_one("#label-vulkan_devices").display = True
                vulkan_devices.clear_options()
                vulkan_devices.add_options(self.add_devices(devices))
            else:
                vulkan_devices.display = False
                self.query_one("#label-vulkan_devices").display = False
                if self.gets("vulkan_devices"):
                    self.dels("vulkan_devices")
        self.settings.save()

    async def update_input_llamacpp_version(self) -> None:
        latest_version = await self.get_latest_llamacpp_version()
        if latest_version <= 0:
            latest_version = 0
        self.query_one("#llamacpp_version").value = "b" + str(latest_version)

    @work(exclusive=True, exit_on_error=False)
    async def work_update_input_llamacpp_version(self) -> None:
        while True:
            await self.update_input_llamacpp_version()
            await asyncio.sleep(600)

    def ensure_is_highlighted(self) -> None:
        side_panel = self.app.query_one("#side-panel")
        side_panel.can_focus = False
        index = side_panel.get_option_index(self.id)
        side_panel.highlighted = index
