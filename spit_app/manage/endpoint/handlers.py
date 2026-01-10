# SPDX-License-Identifier: GPL-2.0
from textual.widgets import Button, Select

class HandlersMixIn:
    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id == "custom-setting-select-add":
            await self.mount_settings_add_custom(event.value)
