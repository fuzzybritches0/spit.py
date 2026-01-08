# SPDX-License-Identifier: GPL-2.0

class ActionsMixIn:
    def action_duplicate(self) -> None:
        self.duplicate()

    async def action_delete(self) -> None:
        self.delete()
        await self.remove_children()
        await self.select_main_screen()

    async def action_save(self) -> None:
        if self.validate_values_edit():
            self.store_values()
            self.save()
            await self.app.maybe_remove("manage-chats")
            await self.remove_children()
            await self.select_main_screen()

    async def action_cancel(self) -> None:
        await self.remove_children()
        await self.select_main_screen()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.children and self.children[0].id == "option-list":
            return False
        if action == "delete" and self.new_manage:
            return False
        return True
