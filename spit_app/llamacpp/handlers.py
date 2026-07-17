import inspect
from textual.events import Focus
from spit_app.textual_message import DownloadFailed, DownloadSuccess
from textual.widgets import Button, Select, Input

class HandlersMixIn:
    async def on_mount(self) -> None:
        await self.edit_manage_screen()
        self.children[2].focus()
        self.work_update_input_llamacpp_version()
        await self.update_input_vulkan_devices()

    async def on_download_failed(self, message: DownloadFailed) -> None:
        callback = getattr(self, f"{message.callback}_failed")
        if inspect.iscoroutinefunction(callback):
            await callback(message.lst)
        else:
            callback(message.lst)

    async def on_download_success(self, message: DownloadSuccess) -> None:
        callback = getattr(self, f"{message.callback}_success")
        if inspect.iscoroutinefunction(callback):
            await callback(message.lst)
        else:
            callback(message.lst)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        id = event.control.id
        if id == "apply-llamacpp-settings":
            if await self.validate_values_edit(["content_length"]):
                await self.button_apply_llamacpp_settings()
        elif id == "update-llamacpp":
            await self.button_update_llamacpp()
        elif id == "delete-llamacpp":
            await self.button_delete_llamacpp()
        elif id == "download-model":
            self.button_download_model()
        elif id == "delete-model":
            self.button_delete-model()
        elif id == "add-custom-model":
            if await self.validate_values_edit(["name", "org", "model", "files"]):
                self.button_add_custom_model()

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
