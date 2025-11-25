# SPDX-License-Identifier: GPL-2.0
from textual.widgets import Button, Header, Footer, OptionList, Select
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container
from spit_app.config.config_screens import ConfigScreensMixIn
from spit_app.config.validation import Validation

class ConfigApp(ModalScreen, ConfigScreensMixIn):
    CSS_PATH = "../styles/config.css"
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("ctrl+s", "set_active", "Set active"),
        ("escape", "dismiss", "Cancel")
    ]

    def __init__(self) -> None:
        super().__init__()
        self.title = f"{self.app.NAME} v{self.app.VERSION} - Configuration"
        self.config = self.app.config
        self.val = Validation(self)

    def compose(self) -> ComposeResult:
        yield Header()
        self.main_container = Container()
        yield self.main_container
        yield Footer()

    async def on_mount(self) -> None:
        self.dyn_container = Container()
        await self.main_container.mount(self.dyn_container)
        await self.select_config_screen()

    def valid_values_add(self) -> bool:
        if not self.query_one("#new-setting").is_valid:
            return False
        if not self.query_one("#new-description").is_valid:
            return False
        stype = self.query_one("#custom-setting-select-add").value
        if stype == "Select":
            if not self.query_one("#new-select-values").is_valid:
                return False
        return True

    def valid_values_edit(self) -> bool:
        for setting, stype, desc, array in self.config.configs[self.cconfig]["custom"]:
            id = setting.replace(".", "-")
            if not stype == "Boolean" and not stype == "Select" and not stype == "Text":
                if not self.query_one(f"#{id}").is_valid:
                    return False
        return True

    def store_values(self) -> None:
        for setting, stype, desc, array in self.config.configs[self.cconfig]["custom"]:
            id = setting.replace(".", "-")
            if stype == "Text":
                newvalue = self.query_one(f"#{id}").text
            else:
                newvalue = self.query_one(f"#{id}").value
            if newvalue == Select.BLANK:
                newvalue = ""
            self.config.store(self.cconfig, setting, stype, newvalue)

    def action_delete(self) -> None:
        self.config.delete_config(self.cconfig)
        self.app.title_update()
        await self.clean_dyn_container()
        await self.select_config_screen()

    def action_set_active(self) -> None:
        if self.valid_values_edit():
            self.store_values()
            self.config.save()
            self.config.set_active(self.cconfig)
            self.app.title_update()
            await self.clean_dyn_container()
            await self.select_config_screen()

    async def action_save(self) -> None:
        if self.valid_values_edit():
            self.store_values()
            self.config.save()
            self.app.title_update()
            await self.clean_dyn_container()
            await self.select_config_screen()

    async def action_add_setting(self) -> None:
        if self.valid_values_add():
            setting = self.query_one("#new-setting").value
            stype = self.query_one("#custom-setting-select-add").value
            desc = self.query_one("#new-description").value
            sarray = []
            if stype == "Select":
                value = self.query_one("#new-select-values").value
                array = value.split(",")
                for el in array:
                    sarray.append(el.strip())
            self.config.add_custom_setting(self.cconfig, setting, stype, desc, sarray)
            self.config.save()
            await self.clean_dyn_container()
            await self.edit_settings_screen()

    async def action_remove_setting(self) -> None:
        remove = self.query_one("#custom-setting-select-remove").value
        if not remove == Select.BLANK:
            self.config.remove_custom_setting(self.cconfig, remove)
            self.config.save()
            await self.clean_dyn_container()
            await self.edit_settings_screen()

    async def action_dismiss(self) -> None:
        if self.dyn_container.children[0].id == "select-config":
            self.dismiss()
        else:
            await self.clean_dyn_container()
            await self.select_config_screen()

    def is_edit_settings(self) -> bool:
        if self.dyn_container.children[0].id == "edit-settings":
            return True
        return False

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "save" or action == "delete" or action == "set_active":
            return self.is_edit_settings()
        return True

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.action_dismiss()
        elif event.button.id == "delete":
            self.action_delete()
        elif event.button.id == "set-active":
            self.action_set_active()
        elif event.button.id == "save":
            self.action_save()
        elif event.button.id == "button-remove-setting":
            await self.action_remove_setting()
        elif event.button.id == "button-add-setting":
            await self.action_add_setting()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "select-new-config":
            self.cconfig = self.config.new()
            await self.clean_dyn_container()
            await self.edit_settings_screen()
        else:
            self.cconfig = int(event.option.id[14:])
            await self.clean_dyn_container()
            await self.edit_settings_screen()
