# SPDX-License-Identifier: GPL-2.0
from textual.widgets import Select
from spit_app.modal_screens import InfoScreen

class ActionsMixIn:
    async def action_add_setting(self) -> None:
        valid, failed = self.validate_add_setting()
        if not valid:
            await self.app.push_screen(InfoScreen("\n".join(failed)))
        else:
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
            await self.mount_setting(setting, stype, desc, sarray)

    async def action_remove_setting(self) -> None:
        remove = self.query_one("#custom-setting-select-remove").value
        if not remove == Select.BLANK:
            self.remove_custom_setting(remove)
            self.query_one("#custom-setting-select-remove").set_options(self.custom_options())
            remove = remove.replace(".", "-")
            await self.query_one(f"#{remove}").remove()
            await self.query_one(f"#label-{remove}").remove()

    async def after_action(self, action: str) -> None:
        if action == "save" or action == "delete":
            await self.app.maybe_remove("manage-chat")
            await self.app.maybe_remove("new-chat")
        if not action == "duplicate":
            await super().after_action(action)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.children and self.children[0].id == "option-list":
            return False
        if not action == "cancel" and not action == "save" and self.new_manage:
            return False
        return True
