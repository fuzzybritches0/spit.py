import os
import shutil
import platform
from textual.widgets import Select
from spit_app.textual_message import DownloadFiles

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
        machine = platform.uname().machine
        if machine == "x86_64":
            machine = "x64"
        elif machine == "aarch64":
            machine = "amd64"
        file = f"llama-b{version}-bin-ubuntu-vulkan-{machine}.tar.gz"
        url = f"https://github.com/ggml-org/llama.cpp/releases/download/b{version}/{file}"
        lst = [(url, self.path["llamacpp"] / file)]
        self.app.post_message(DownloadFiles(self, lst, "update_llamacpp"))

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

    def button_download_model(self) -> None:
        model = self.get_model(self.query_one("#download_model").value)
        path = self.path["models"] / model["id"]
        path.mkdir(parents=True, exist_ok=True)
        lst = []
        for file in model["files"]:
            url = f"https://huggingface.co/{model['org']}/{model['model']}/resolve/main/{file}?download=true"
            lst.append((url, path / file))
        self.app.post_message(DownloadFiles(self, lst, "download_model"))
