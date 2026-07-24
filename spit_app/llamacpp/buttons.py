import os
import shutil
from textual.widgets import Select
from spit_app.textual_message import DownloadFiles

class ButtonsMixIn:
    async def button_apply_llamacpp_settings(self) -> None:
        self.puts("active_version")
        self.puts("active_models")
        self.puts("server_port")
        self.puts("timeout")
        self.puts("cache_prompt")
        self.puts("vulkan_devices")
        self.puts("server_port")
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
        file = self.get_llamacpp_file(version)
        url = f"https://github.com/ggml-org/llama.cpp/releases/download/b{version}/{file}"
        lst = [(url, str(self.path["llamacpp"] / file))]
        self.app.post_message(DownloadFiles(self.id, f"b{version}", lst, "update_llamacpp"))

    async def button_delete_llamacpp(self) -> None:
        selection = self.query_one("#delete_version").value
        if selection == Select.NULL:
            return None
        path = self.path["llamacpp"] / f"llama-{selection}"
        shutil.rmtree(path)
        await self.update_llamacpp_success()
        if selection == self.gets("active_version"):
            self.query_one("#active_version").value = Select.NULL
            self.puts("active_version")
        file = self.get_llamacpp_file(int(selection[1:]))
        self.app.del_downloads_size([str(self.path["llamacpp"] / file)])
        self.settings.save()
        await self.update_input_vulkan_devices()
        self.app.action_notify(f"Llama.cpp version {selection} deleted!")

    def button_download_model(self) -> None:
        model_id = self.query_one("#download_model").value
        if model_id == Select.NULL:
            return None
        model = self.get_model(model_id)
        path = self.path["models"] / model_id
        path.mkdir(parents=True, exist_ok=True)
        lst = []
        for file in model["files"]:
            url = f"https://huggingface.co/{model['org']}/{model['model']}/resolve/main/{file}?download=true"
            lst.append((url, str(path / file)))
        self.app.post_message(DownloadFiles(self.id, model["name"], lst, "download_model"))

    async def button_delete_model(self) -> None:
        deleted = False
        model_id = self.query_one("#download_model").value
        if model_id == Select.NULL:
            return None
        model = self.get_model(self.query_one("#download_model").value)
        model_name = model["name"]
        model_files = model["files"]
        path = self.path["models"] / model_id
        if os.path.exists(path):
            shutil.rmtree(path)
            files = []
            for file in model_files:
                files.append(str(self.path["models"] / model_id / file))
            self.app.del_downloads_size(files)
            self.settings.save()
            await self.download_model_success()
            self.app.action_notify(f"{model_name} files deleted!")
        if self.gets("custom_models") and self.gets("custom_models", model_id):
            self.dels("custom_models", model_id)
            self.settings.save()
            await self.download_model_success()
            self.app.action_notify(f"Entry for custom model {model_name} deleted!")
        if self.gets("server_settings") and self.gets("server_settings", model_id):
            self.dels("server_settings", model_id)
            self.query_one("#download_model").value = Select.NULL
            self.settings.save()
            self.app.action_notify(f"Server settings for {model_name} deleted!")

    async def button_add_custom_model(self) -> None:
        custom_model = {
            "name": self.query_one("#name").value,
            "org": self.query_one("#org").value,
            "model": self.query_one("#model").value,
            "files": self.query_one("#files").value,
        }
        if not "custom_models" in self.settings.llamacpp:
            self.settings.llamacpp["custom_models"] = {}
        self.puts("custom_models", self.app.get_rand_seq(32), custom_model)
        self.settings.save()
        await self.download_model_success()
        self.app.action_notify(f"Model data saved! You can now try downloading it above!")
