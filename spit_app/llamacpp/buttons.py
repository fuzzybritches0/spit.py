import os
import shutil
from textual.widgets import Select

class ButtonsMixIn:
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
        self.update_llamacpp(version)

    async def button_delete_llamacpp(self) -> None:
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
