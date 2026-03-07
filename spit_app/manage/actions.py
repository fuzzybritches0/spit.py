# SPDX-License-Identifier: GPL-2.0
from textual import work
from spit_app.modal_screens import ConfirmScreen

class ActionsMixIn:
    async def after_action(self, action: str) -> None:
        await self.remove_children()
        await self.select_main_screen()

    def action_duplicate(self) -> None:
        self.duplicate()

    @work
    async def action_delete(self) -> None:
        if await self.app.push_screen_wait(ConfirmScreen()):
            self.delete()
            await self.after_action("delete")

    async def action_save(self) -> None:
        if await self.validate_values_edit():
            self.store_values()
            self.save()
            await self.after_action("save")

    async def action_cancel(self) -> None:
        await self.after_action("cancel")
