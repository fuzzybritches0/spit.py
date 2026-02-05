# SPDX-License-Identifier: GPL-2.0
from spit_app.modal_screens import InfoScreen

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
        valid, failed = self.validate_values_edit()
        if not valid:
            await self.app.push_screen(InfoScreen("\n".join(failed)))
        else:
            self.store_values()
            self.save()
            await self.after_action("save")

    async def action_cancel(self) -> None:
        await self.after_action("cancel")
