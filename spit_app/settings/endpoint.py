# SPDX-License-Identifier: GPL-2.0
from textual.widgets import Button, OptionList, Select
from spit_app.settings.validation import Validation

class EndpointMixIn():
    def init(self) -> None:
        self.val = Validation(self)

    def valid_values_add(self) -> bool:
        if not self.query_one("#new-setting").is_valid:
            return False
        if not self.query_one("#new-description").is_valid:
            return False
        stype = self.query_one("#custom-setting-select-add").value
        if stype == "Select" or stype == "Select_no_default":
            if not self.query_one("#new-select-values").is_valid:
                return False
        return True

    def valid_values_edit(self) -> bool:
        for setting, stype, desc, array in self.settings.endpoints[self.cur_endpoint]["custom"]:
            id = setting.replace(".", "-")
            if (not stype == "Boolean" and not stype == "Select" and
                not stype == "Select_no_default" and not stype == "Text"):
                if not self.query_one(f"#{id}").is_valid:
                    return False
        return True

    def store_values(self) -> None:
        for setting, stype, desc, array in self.settings.endpoints[self.cur_endpoint]["custom"]:
            id = setting.replace(".", "-")
            if stype == "Text":
                newvalue = self.query_one(f"#{id}").text
            else:
                newvalue = self.query_one(f"#{id}").value
            if newvalue == Select.BLANK:
                newvalue = ""
            self.settings.store(self.cur_endpoint, setting, stype, newvalue)

    async def action_delete(self) -> None:
        self.settings.delete_endpoint(self.cur_endpoint)
        self.app.title_update()
        await self.clean_dyn_container()
        await self.select_main_screen()

    async def action_set_active(self) -> None:
        if self.valid_values_edit():
            self.store_values()
            self.settings.save()
            self.settings.set_active(self.cur_endpoint)
            self.app.title_update()
            await self.clean_dyn_container()
            await self.select_main_screen()

    async def action_save(self) -> None:
        if self.valid_values_edit():
            self.store_values()
            self.settings.save()
            self.app.title_update()
            await self.clean_dyn_container()
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
            await self.clean_dyn_container()
            await self.edit_endpoint_screen()

    async def action_remove_setting(self) -> None:
        remove = self.query_one("#custom-setting-select-remove").value
        if not remove == Select.BLANK:
            self.settings.remove_custom_setting(self.cur_endpoint, remove)
            self.settings.save()
            await self.clean_dyn_container()
            await self.edit_endpoint_screen()

    async def action_dismiss(self) -> None:
        if self.dyn_container.children[0].id == "select-main":
            self.dismiss()
        else:
            self.settings.load()
            await self.clean_dyn_container()
            await self.select_main_screen()

    def is_edit_endpoint(self) -> bool:
        if self.dyn_container.children[0].id == "edit-endpoint":
            return True
        return False

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "save" or action == "delete" or action == "set_active":
            return self.is_edit_endpoint()
        return True

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
