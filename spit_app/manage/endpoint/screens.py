# SPDX-License-Identifier: GPL-2.0
from textual.validation import Function
from textual.widgets import Input, TextArea, Switch, Label, Button, OptionList, Select, Rule
from textual.widgets.option_list import Option
from textual.containers import Horizontal

class ScreensMixIn:
    async def mount_custom_setting_form(self, stype) -> None:
        await self.mount(Label(f"Setting for {stype} value:"))
        valsetting = [Function(self.is_not_empty), Function(self.is_unique_custom),
                      Function(self.is_valid_setting)]
        await self.mount(Input(id="new-setting", validators=valsetting, max_length=128))
        await self.mount(Label(f"Description for {stype} value:"))
        await self.mount(Input(id="new-description", validators=[Function(self.is_not_empty)]))
        if stype == "select" or stype == "select_no_default":
            await self.mount(Label("Select values (separate with ','):"))
            valselect = [Function(self.is_not_empty), Function(self.is_valid_selection)]
            await self.mount(Input(id="new-select-values", validators=valselect))
        await self.mount(Button("Add", id=f"add-setting"))

    async def mount_settings_add_custom(self, stype) -> None:
        while not self.children[-1].id == "custom-setting-select-add":
            await self.children[-1].remove()
        if not stype == Select.BLANK:
            await self.mount_custom_setting_form(stype)

    async def edit_manage_add_custom(self) -> None:
        types = [("Integer", "integer"),
                 ("Unsigned Integer", "uinteger"),
                 ("Float", "float"),
                 ("Unsigned Float", "ufloat"),
                 ("Boolean", "boolean"),
                 ("String", "string"),
                 ("Text", "text"),
                 ("Select", "select"),
                 ("Select (no default)", "select_no_default")
        ]
        await self.mount(Label("Add custom setting:"))
        await self.mount(Select(types, id="custom-setting-select-add", allow_blank=False))

    def custom_options(self) -> list:
        options = []
        for setting in self.manage.keys():
            if (not setting == "name" and
                not setting == "endpoint_url" and
                not setting == "key" and
                not setting == "reasoning_key"):
                options.append((setting, setting))
        return options

    async def edit_manage_remove_custom(self) -> None:
        await self.mount(Label("Remove custom setting:"))
        await self.mount(Select(self.custom_options(), id="custom-setting-select-remove", prompt="None"))
        await self.mount(Button("Remove", id="remove-setting"))

    async def edit_manage_screen(self) -> None:
        await super().edit_manage_screen()
        await self.mount(Rule())
        await self.edit_manage_remove_custom()
        await self.mount(Rule())
        await self.edit_manage_add_custom()
