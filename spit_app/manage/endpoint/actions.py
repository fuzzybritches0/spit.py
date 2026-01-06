# SPDX-License-Identifier: GPL-2.0
from textual.widgets import Select

class ActionsMixIn:
    def action_duplicate(self) -> None:
        self.duplicate()

    async def action_delete(self) -> None:
        self.delete()
        await self.remove_children()
        await self.select_main_screen()

    async def action_save(self) -> None:
        if self.valid_values_edit():
            self.store_values()
            self.save()
            await self.app.maybe_remove("manage-chats")
            await self.remove_children()
            await self.select_main_screen()

    async def action_add_setting(self) -> None:
        setting = self.query_one("#new-setting").value
        stype = self.query_one("#custom-setting-select-add").value
        desc = self.query_one("#new-description").value
        sarray = []
        if stype == "select" or stype == "select_no_default":
            value = self.query_one("#new-select-values").value
            array = value.split(",")
            for el in array:
                sarray.append(el.strip())
        self.add_custom_setting(setting, stype, desc, sarray)
        self.query_one("#custom-setting-select-remove").set_options(self.custom_options())
        await self.mount_setting(setting, stype, desc, sarray, True)

    async def action_remove_setting(self) -> None:
        remove = self.query_one("#custom-setting-select-remove").value
        if not remove == Select.BLANK:
            self.remove_custom_setting(remove)
            self.query_one("#custom-setting-select-remove").set_options(self.custom_options())
            remove = remove.replace(".", "-")
            await self.query_one(f"#{remove}").remove()
            await self.query_one(f"#label-{remove}").remove()

    async def action_cancel(self) -> None:
        await self.remove_children()
        await self.select_main_screen()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.children and self.children[0].id == "option-list":
            return False
        if action == "delete" and self.new_endpoint:
            return False
        return True
