# SPDX-License-Identifier: GPL-2.0
from textual.widgets import Button, OptionList, Select

class HandlersMixIn:
    async def on_mount(self) -> None:
        await self.select_main_screen()

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id == "custom-setting-select-add":
            await self.mount_settings_add_custom(event.value)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            await self.action_cancel()
        elif event.button.id == "delete":
            await self.action_delete()
        elif event.button.id == "save":
            await self.action_save()
        elif event.button.id == "button-remove-setting":
            await self.action_remove_setting()
        elif event.button.id == "button-add-setting":
            await self.action_add_setting()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "select-new-endpoint":
            self.new()
            await self.remove_children()
            await self.edit_endpoint_screen()
        else:
            self.load(str(event.option.id[16:]))
            await self.remove_children()
            await self.edit_endpoint_screen()
