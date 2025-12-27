# SPDX-License-Identifier: GPL-2.0
from textual.widgets import Select

class ActionsMixIn:
    async def action_delete(self) -> None:
        self.settings.delete_endpoint(self.cur_endpoint)
        await self.remove_children()
        await self.select_main_screen()

    async def action_save(self) -> None:
        if self.valid_values_edit():
            self.store_values()
            self.settings.save()
            await self.remove_children()
            await self.select_main_screen()

    async def action_add_setting(self) -> None:
        if self.valid_values_add():
            setting = self.query_one("#new-setting").value
            stype = self.query_one("#custom-setting-select-add").value
            desc = self.query_one("#new-description").value
            sarray = []
            if stype == "Select" or stype == "Select_no_default":
                value = self.query_one("#new-select-values").value
                array = value.split(",")
                for el in array:
                    sarray.append(el.strip())
            self.settings.add_custom_setting(self.cur_endpoint, setting, stype, desc, sarray)
            self.settings.save()
            await self.remove_children()
            await self.edit_endpoint_screen()

    async def action_remove_setting(self) -> None:
        remove = self.query_one("#custom-setting-select-remove").value
        if not remove == Select.BLANK:
            self.settings.remove_custom_setting(self.cur_endpoint, remove)
            self.settings.save()
            await self.remove_children()
            await self.edit_endpoint_screen()

    async def action_cancel(self) -> None:
        self.settings.load()
        await self.remove_children()
        await self.select_main_screen()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.children and self.children[0].id == "option-list":
            return False
        return True
