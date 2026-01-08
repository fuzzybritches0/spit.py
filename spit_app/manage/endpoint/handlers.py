# SPDX-License-Identifier: GPL-2.0
from textual.widgets import Button, Select

class HandlersMixIn:
    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id == "custom-setting-select-add":
            await self.mount_settings_add_custom(event.value)

    async def on_button_pressed_extra(self, event: Button.Pressed) -> None:
        if event.button.id == "button-remove-setting":
            await self.action_remove_setting()
        elif event.button.id == "button-add-setting":
            await self.action_add_setting()
