import os
import shutil
import tarfile
import asyncio
from textual import work
from textual.events import Focus
from .helpers import download_llamacpp, get_latest_llamacpp_version
from spit_app.modal_screens import ProgressBarScreen
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Label, Button, Select, Input, Rule

class Llamacpp(VerticalScroll):
    BINDINGS = [
        ("u", "update", "Update Llamacpp"),
        ("s", "set_active", "Set Active"),
        ("d", "delete", "Delete")
    ]

    def __init__(self) -> None:
        super().__init__()
        self.id = "manage-llamacpp"
        self.classes = "manage"
        self.settings = self.app.settings
        self.path = self.app.settings.path

    def get_llamacpp_versions(self) -> tuple:
        versions = ()
        for item in os.listdir(self.path["llamacpp"]):
            if os.path.isdir(self.path["llamacpp"] / item):
                version = item[6:]
                versions += ((version, version),)
        return versions

    def update_label(self, version: str) -> str:
        return f"\nActive llama.cpp version: [bold $accent]{version}\n"

    def compose(self) -> None:
        yield Label("Manage llama.cpp server installations:\n\nVersion:\n")
        yield Input(value="", id="input-llamacpp-version")
        yield Button("Download", id="update-llamacpp")
        yield Rule()
        selected = self.settings.llamacpp["selected"]
        yield Label(self.update_label(selected), id="active-version")
        llamacpp_versions = self.get_llamacpp_versions()
        yield Select(llamacpp_versions, value=Select.NULL, id="select-llamacpp-version", prompt="None")
        with Horizontal(classes="auto-height"):
            yield Button("Set Active", id="set-active")
            yield Button("Delete", id="delete-selected")
        yield Rule()
        yield Label("Manage llama.cpp models:\n\n")

    def on_mount(self) -> None:
        self.children[1].focus()
        self.work_update_input_llamacpp_version()

    async def update_input_llamacpp_version(self) -> None:
        latest_version = await get_latest_llamacpp_version(self.settings)
        if latest_version <= 0:
            latest_version = 0
        self.query_one("#input-llamacpp-version").value = "b" + str(latest_version)

    @work(exclusive=True, exit_on_error=False)
    async def work_update_input_llamacpp_version(self) -> None:
        while True:
            await self.update_input_llamacpp_version()
            await asyncio.sleep(600)

    def update_options(self) -> None:
        self.query_one("#select-llamacpp-version").set_options(self.get_llamacpp_versions())

    async def update_llamacpp(self, progress_bar, version: str) -> None:
        success = await download_llamacpp(progress_bar, self.path["llamacpp"], version, self.update_options)
        if not success:
            failed_version = self.query_one("#input-llamacpp-version").value
            self.app.exception = Exception(f"Could not download {failed_version}!")
            await self.update_input_llamacpp_version()

    async def button_update_llamacpp(self) -> None:
        version = self.query_one("#input-llamacpp-version").value
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

    def set_active(self, selection: str|None = None) -> None:
        self.query_one("#active-version").update(self.update_label(selection))
        self.settings.llamacpp["selected"] = selection
        self.settings.save()

    def button_set_active(self) -> None:
        selection = self.query_one("#select-llamacpp-version").value
        if selection == Select.NULL:
            selection = None
        self.set_active(selection)

    def button_delete_selected(self) -> None:
        selection = self.query_one("#select-llamacpp-version").value
        if selection == Select.NULL:
            return None
        path = self.path["llamacpp"] / f"llama-{selection}"
        shutil.rmtree(path)
        self.update_options()
        if selection == self.settings.llamacpp["selected"]:
            self.set_active()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.control.id == "update-llamacpp":
            await self.button_update_llamacpp()
        elif event.control.id == "set-active":
            self.button_set_active()
        elif event.control.id =="delete-selected":
            self.button_delete_selected()

    async def action_update(self) -> None:
        await self.button_update_llamacpp()

    def action_set_active(self) -> None:
        self.button_set_active()

    def action_delete(self) -> None:
        self.button_delete_selected()

    async def on_focus(self, event: Focus) -> None:
        event.prevent_default()
        self.children[1].focus()
        self.ensure_is_highlighted()
        await self.update_input_llamacpp_version()

    def ensure_is_highlighted(self) -> None:
        side_panel = self.app.query_one("#side-panel")
        side_panel.can_focus = False
        index = side_panel.get_option_index(self.id)
        side_panel.highlighted = index
