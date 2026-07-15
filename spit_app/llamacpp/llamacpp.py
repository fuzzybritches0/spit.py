import os
import shutil
import tarfile
import asyncio
from textual import work
from textual.app import ComposeResult
from textual.events import Focus
from .helpers import download_llamacpp, get_latest_llamacpp_version, download_model, get_vulkan_devices
from spit_app.modal_screens import ProgressBarScreen
from spit_app.manage.validation import ValidationMixIn
from spit_app.manage.input_widget import InputWidget
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Label, Button, Select, Input, Rule
from .models import MODELS

class Llamacpp(VerticalScroll, ValidationMixIn):
    def __init__(self) -> None:
        super().__init__()
        self.id = "manage-llamacpp"
        self.classes = "manage"
        self.manage = {
            "active_version": {"stype": "select", "desc": "Active Version", "ameth": "get_versions"},
            "active_model": {"stype": "select", "desc": "Active Model", "ameth": "get_models"},
            "content_length": {"stype": "uinteger", "empty": False, "desc": "Content Length (0 = model default)"},
            "server_arguments": {"stype": "string", "desc": "Server Arguments", "empty": True},
            "vulkan_devices": {"stype": "select_list", "desc": "Use Vulkan devices", "options": []},
            "llamacpp_version":{"stype": "string", "empty": False, "desc": "Llama.cpp Version"},
            "delete_version": {"stype": "select", "desc": "Version", "ameth": "get_versions"},
            "download_model": {"stype": "select", "desc": "Manage Models", "ameth": "get_models_list"},
            "name": {"stype": "string", "empty": False, "desc": "Model Identifier"},
            "org": {"stype": "string", "empty": False, "desc": "Organisation"},
            "model": {"stype": "string", "empty": False, "desc": "Model"},
            "files": {"stype": "string", "empty": False, "desc": "Files"},
            "custom_models": {"stype": "list"}
        }
        self.settings = self.app.settings
        self.path = self.app.settings.path
        self.focused_widget = None

    def gets(self, setting: str) -> any:
        if setting in self.settings.llamacpp and self.settings.llamacpp[setting]:
            return self.settings.llamacpp[setting]
        if not setting in self.settings.llamacpp or not self.settings.llamacpp[setting]:
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
            if self.manage[setting]["stype"] == "list":
                return []


    def puts(self, setting: str) -> None:
        if self.manage[setting]["stype"] == "select_list":
            value = self.query_one(f"#{setting}").selected
        else:
            value = self.query_one(f"#{setting}").value
        if value == Select.NULL:
            value = None
        self.settings.llamacpp[setting] = value

    def get_versions(self) -> tuple:
        versions = ()
        for item in os.listdir(self.path["llamacpp"]):
            if os.path.isdir(self.path["llamacpp"] / item):
                version = item[6:]
                versions += ((version, version),)
        return versions

    def get_models_list(self) -> tuple:
        models = ()
        for model in MODELS:
            models += ((model["name"], model["name"]),)
        if self.gets("custom_models"):
            for model in self.gets("custom_models"):
                models += ((model["name"], model["name"]),)
        return models

    def get_models(self) -> tuple:
        models = ()
        for model in os.listdir(self.path["models"]):
            if os.path.isdir(self.path["models"] / model):
                model = model.split("-")[1:]
                models += ((model, model),)
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

    async def on_mount(self) -> None:
        await self.edit_manage_screen()
        self.children[2].focus()
        self.work_update_input_llamacpp_version()
        await self.update_input_vulkan_devices()

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
            if "active_version" in self.settings.llamacpp and self.settings.llamacpp["active_version"]:
                llamacpp = self.path["llamacpp"] / ("llama-" + self.settings.llamacpp["active_version"])
                devices = await get_vulkan_devices(llamacpp)
                if devices:
                    self.query_one("#vulkan_devices").display = True
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

    async def update_llamacpp(self, progress_bar, version: str) -> None:
        success = await download_llamacpp(progress_bar, self.path["llamacpp"], version, self.update_options)
        if not success:
            failed_version = self.query_one("#llamacpp_version").value
            self.app.exception = Exception(f"Could not download {failed_version}!")
            await self.update_input_llamacpp_version()
        await self.update_input_vulkan_devices()

    async def button_apply_llamacpp_settings(self) -> None:
        self.puts("active_version")
        self.puts("active_model")
        self.puts("vulkan_devices")
        self.puts("content_length")
        self.puts("server_arguments")
        self.settings.save()
        self.app.action_notify("Changes applied!")
        await self.update_input_vulkan_devices()

    async def button_update_llamacpp(self) -> None:
        version = self.query_one("#llamacpp_version").value
        if os.path.isdir(self.path["llamacpp"] / f"llama-{version}"):
            self.app.exception = Exception(f"Info: {version} already downloaded! To re-download, delete first!")
            await self.update_input_llamacpp_version()
            return None
        if version.startswith("b"):
            version = version[1:]
        try:
            version = int(version)
        except:
            version = None
        if not version:
            self.app.exception = Exception("Invalid version provided!")
            await self.update_input_llamacpp_version()
            return None
        progress_bar = ProgressBarScreen(self)
        self.app.push_screen(progress_bar)
        self.work = self.run_worker(self.update_llamacpp(progress_bar, version))

    async def button_delete_selected(self) -> None:
        selection = self.query_one("#delete_version").value
        if selection == Select.NULL:
            return None
        path = self.path["llamacpp"] / f"llama-{selection}"
        shutil.rmtree(path)
        self.update_options()
        if selection == self.gets("active_version"):
            self.query_one("#active_version").value = Select.NULL
            self.puts("active_version")
            self.settings.save()
        await self.update_input_vulkan_devices()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        id = event.control.id
        if id == "update-llamacpp":
            await self.button_update_llamacpp()
        elif id =="delete-llamacpp":
            await self.button_delete_selected()
        elif id == "apply-llamacpp-settings":
            if await self.validate_values_edit(["content_length"]):
                await self.button_apply_llamacpp_settings()

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.validation_result:
            await self.update_val_results_input(event.control.id, event.validation_result.failure_descriptions)

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id == "active_version":
            self.puts("active_version")
            await self.update_input_vulkan_devices()

    async def on_focus(self, event: Focus) -> None:
        event.prevent_default()
        if self.focused_widget:
            self.focused_widget.focus()
        else:
            self.children[2].focus()
        self.ensure_is_highlighted()
        await self.update_input_llamacpp_version()

    def on_descendant_focus(self) -> None:
        self.focused_widget = self.app.focused

    def ensure_is_highlighted(self) -> None:
        side_panel = self.app.query_one("#side-panel")
        side_panel.can_focus = False
        index = side_panel.get_option_index(self.id)
        side_panel.highlighted = index
