# SPDX-License-Identifier: GPL-2.0
from textual.validation import Function
from textual.widgets import Input, TextArea, Switch, Label, Button, OptionList, Select, Rule
from textual.widgets.option_list import Option
from textual.containers import Horizontal

class ScreensMixIn:
    async def mount_custom_setting_form(self, stype) -> None:
        await self.mount(Label(f"Setting for {stype} value:"))
        Validators = [ Function(self.is_unique_custom), Function(self.is_valid_setting) ]
        await self.mount(Input(id="new-setting",
                                       validators=Validators,
                                       restrict=r"[0-9a-z_.]*",
                                       valid_empty=False,
                                       max_length=128))
        await self.mount(Label(f"Description for {stype} value:"))
        await self.mount(Input(id="new-description", validators=[Function(self.is_not_empty)]))
        if stype == "select" or stype == "select_no_default":
            await self.mount(Label("Select values (separate with ','):"))
            Validators = [ Function(self.is_valid_selection) ]
            await self.mount(Input(id="new-select-values", validators=Validators,
                                           restrict=r"[0-9a-z_, ]*"))
        await self.mount(Button("Add", id=f"button-add-setting"))

    async def mount_settings_add_custom(self, stype) -> None:
        while not self.children[-1].id == "custom-setting-select-add":
            await self.children[-1].remove()
        if not stype == Select.BLANK:
            await self.mount_custom_setting_form(stype)

    async def edit_endpoint_add_custom(self) -> None:
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
        await self.mount(Select.from_values(types, id="custom-setting-select-add", allow_blank=False))

    def custom_options(self) -> list:
        options = []
        for setting in self.endpoint.keys():
            if (not setting == "name" and
                not setting == "endpoint_url" and
                not setting == "key" and
                not setting == "reasoning_key"):
                options.append((setting, setting))
        return options

    async def edit_endpoint_remove_custom(self) -> None:
        await self.mount(Label("Remove custom setting:"))
        await self.mount(Select(self.custom_options(), id="custom-setting-select-remove", prompt="None"))
        await self.mount(Button("Remove", id="button-remove-setting"))

    async def mount_setting(self, setting: str, stype: str, desc: str, amore: list, add: bool = False) -> None:
        id = setting.replace(".", "-")
        if add:
            await self.mount(Label(f"{desc}: ({stype})", id="label-"+id), before="#save-delete-cancel")
        else:
            await self.mount(Label(f"{desc}: ({stype})", id="label-"+id))
        value = None
        if "value" in self.endpoint[setting]:
            value = self.endpoint[setting]["value"]
        if value is None:
            value = ""
        Validators = []
        vtype = "text"
        if setting == "name":
            Validators.append(Function(self.is_unique_name))
        elif setting == "endpoint_url":
            Validators.append(Function(self.is_url))
        else:
            if stype == "float":
                vtype = "number"
            elif stype == "integer":
                vtype = "integer"
        if stype == "float" or stype == "integer":
            value=str(value)
        if stype == "select":
            if not value:
                value = Select.BLANK
            if add:
                await self.mount(Select.from_values(amore, id=id, value=value,
                                                prompt="Default"), before="#save-delete-cancel")
            else:
                await self.mount(Select.from_values(amore, id=id, value=value, prompt="Default"))
        elif stype == "select_no_default":
            if not value:
                value = amore[0]
            if add:
                await self.mount(Select.from_values(amore, id=id, value=value,
                                allow_blank=False), before="#save-delete-cancel")
            else:
                await self.mount(Select.from_values(amore, id=id, value=value, allow_blank=False))
        elif stype == "boolean":
            if add:
                await self.mount(Switch(id=id, value=value), before="#save-delete-cancel")
            else:
                await self.mount(Switch(id=id, value=value))
        elif stype == "text":
            if add:
                await self.mount(TextArea(value, id=id, classes="text-area"), before="#save-delete-cancel")
            else:
                await self.mount(TextArea(value, id=id, classes="text-area"))
        else:
            if add:
                await self.mount(Input(type=vtype, validators=Validators,
                                      id=f"{setting}", value=value), before="#save-delete-cancel")
            else:
                await self.mount(Input(type=vtype, validators=Validators,
                                      id=f"{setting}", value=value))

    async def edit_endpoint(self) -> None:
        for setting in self.endpoint.keys():
            options = []
            if "options" in self.endpoint[setting]:
                options = self.endpoint[setting]["options"]
            await self.mount_setting(setting, self.endpoint[setting]["stype"],
                                     self.endpoint[setting]["desc"], options)

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
                    Button("Duplicate", id="duplicate"),
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
            name=self.settings.endpoints[endpoint]["name"]["value"]
            Options.append(Option(f"\nEdit: {name}\n", id=f"select-endpoint-{endpoint}"))
        await self.mount(OptionList(*Options, id="option-list"))
        self.children[0].focus()
