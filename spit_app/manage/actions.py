# SPDX-License-Identifier: GPL-2.0

class ActionsMixIn:
    async def after_action(self, action: str) -> None:
        await self.remove_children()
        await self.select_main_screen()

    def action_duplicate(self) -> None:
        self.duplicate()

    async def action_delete(self) -> None:
        self.delete()
        await self.after_action("delete")

    async def action_save(self) -> None:
        if self.validate_values_edit():
            self.store_values()
            self.save()
            if not self.id == "manage-chat":
                await self.app.maybe_remove("manage-chat")
            if not self.id == "new-chat":
                await self.app.maybe_remove("new-chat")
            await self.after_action("save")

    async def action_cancel(self) -> None:
        await self.after_action("cancel")
