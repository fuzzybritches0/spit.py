# SPDX-License-Identifier: GPL-2.0
from textual.widgets import Button, OptionList

class HandlersMixIn():
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            await self.action_dismiss()
        elif event.button.id == "delete":
            await self.action_delete()
        elif event.button.id == "set-active":
            await self.action_set_active()
        elif event.button.id == "save":
            await self.action_save()
        elif event.button.id == "button-remove-setting":
            await self.action_remove_setting()
        elif event.button.id == "button-add-setting":
            await self.action_add_setting()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "select-new-endpoint":
            self.cur_endpoint = self.settings.new()
            await self.clean_dyn_container()
            await self.edit_endpoint_screen()
        else:
            self.cur_endpoint = int(event.option.id[16:])
            await self.clean_dyn_container()
            await self.edit_endpoint_screen()
