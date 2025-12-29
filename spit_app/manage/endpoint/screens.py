# SPDX-License-Identifier: GPL-2.0
from textual.validation import Function
from textual.widgets import Input, TextArea, Switch, Label, Button, OptionList, Select, Rule
from textual.widgets.option_list import Option
from textual.containers import Horizontal

class ScreensMixIn:
    async def mount_custom_setting_form(self, stype) -> None:
        await self.mount(Label(f"Setting for {stype} value:"))
        Validators = [ Function(self.val.is_unique_custom), Function(self.val.is_valid_setting) ]
        await self.mount(Input(id="new-setting",
                                       validators=Validators,
                                       restrict=r"[0-9a-z_.]*",
                                       valid_empty=False,
                                       max_length=128))
        await self.mount(Label(f"Description for {stype} value:"))
        await self.mount(Input(id="new-description", validators=[Function(self.val.is_not_empty)]))
        if stype == "Select" or stype == "Select_no_default":
            await self.mount(Label("Select values (separate with ','):"))
            Validators = [ Function(self.val.is_valid_selection) ]
            await self.mount(Input(id="new-select-values", validators=Validators,
                                           restrict=r"[0-9a-z_, ]*"))
        await self.mount(Button("Add", id=f"button-add-setting"))

    async def mount_settings_add_custom(self, stype) -> None:
        while not self.children[-1].id == "custom-setting-select-add":
            await self.children[-1].remove()
        if not stype == Select.BLANK:
            await self.mount_custom_setting_form(stype)

    async def edit_endpoint_add_custom(self) -> None:
        types = [ "Integer", "Float", "Boolean", "String", "Text", "Select", "Select_no_default" ]
        await self.mount(Label("Add custom setting:"))
        await self.mount(Select.from_values(types, id="custom-setting-select-add", allow_blank=False))

    def custom_options(self) -> list:
        options = []
        for setting, *others in self.settings.endpoints[self.cur_endpoint]["custom"]:
            if (not setting == "name" and
                not setting == "endpoint_url" and
                not setting == "key" and
                not setting == "reasoning_key"):
                options.append((setting, setting))
        return options

    async def edit_endpoint_remove_custom(self) -> None:
        await self.mount(Label("Remove custom setting:"))
        await self.mount(Select(self.custom_options(), id="custom-setting-select-remove", allow_blank=False))
        await self.mount(Button("Remove", id="button-remove-setting"))

    async def edit_endpoint(self) -> None:
        for setting, stype, desc, amore in self.settings.endpoints[self.cur_endpoint]["custom"]:
            id = setting.replace(".", "-")
            await self.mount(Label(f"{desc}: ({stype})"))
            value = None
            if setting in self.settings.endpoints[self.cur_endpoint]["values"]:
                value = self.settings.endpoints[self.cur_endpoint]["values"][setting]
            if value is None:
                value = ""
            Validators = []
            vtype = "text"
            if setting == "name":
                Validators.append(Function(self.val.is_unique_name))
            elif setting == "endpoint_url":
                Validators.append(Function(self.val.is_url))
            else:
                if stype == "Float":
                    vtype = "number"
                elif stype == "Integer":
                    vtype = "integer"
            if stype == "Float" or stype == "Integer":
                value=str(value)
            if stype == "Select":
                if not value:
                    value = Select.BLANK
                await self.mount(Select.from_values(amore, id=id, value=value, prompt="Default"))
            elif stype == "Select_no_default":
                if not value:
                    value = amore[0]
                await self.mount(Select.from_values(amore, id=id, value=value, allow_blank=False))
            elif stype == "Boolean":
                await self.mount(Switch(id=id, value=value))
            elif stype == "Text":
                await self.mount(TextArea(value, id=id, classes="text-area"))
            else:
                await self.mount(Input(type=vtype, validators=Validators,
                                          id=f"{setting}", value=value))

    async def edit_endpoint_screen(self) -> None:
        await self.edit_endpoint()
        if self.new_endpoint:
            await self.mount(Horizontal(
                    Button("Save", id="save"),
                    Button("Cancel", id="cancel"),
                    id="save-delete-cancel"
            ))
        else:
            await self.mount(Horizontal(
                    Button("Save", id="save"),
                    Button("Delete", id="delete"),
                    Button("Cancel", id="cancel"),
                    id="save-delete-cancel"
            ))
        await self.mount(Rule())
        await self.edit_endpoint_remove_custom()
        await self.mount(Rule())
        await self.edit_endpoint_add_custom()
        self.children[1].focus()

    async def select_main_screen(self) -> None:
        Options = [ Option("\nCreate new endpoint\n", id="select-new-endpoint") ]
        for endpoint in self.settings.endpoints.keys():
            name=self.settings.endpoints[endpoint]["values"]["name"]
            Options.append(Option(f"\nEdit: {name}\n", id=f"select-endpoint-{endpoint}"))
        await self.mount(OptionList(*Options, id="option-list"))
        self.children[0].focus()
