# SPDX-License-Identifier: GPL-2.0
from textual.validation import Function
from textual.widgets import Input, TextArea, Switch, Label, Button, OptionList, Select, Rule
from textual.widgets.option_list import Option
from textual.containers import VerticalScroll, Horizontal

class ScreensMixIn:
    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.control.id == "custom-setting-select-add":
            await self.mount_settings_add_custom(event.value)

    async def mount_custom_setting_form(self, stype) -> None:
        await self.vscroll.mount(Label(f"Setting for {stype} value:"))
        Validators = [ Function(self.val.is_unique_custom), Function(self.val.is_valid_setting) ]
        await self.vscroll.mount(Input(id="new-setting",
                                       validators=Validators,
                                       restrict=r"[0-9a-z_.]*",
                                       valid_empty=False,
                                       max_length=128))
        await self.vscroll.mount(Label(f"Description for {stype} value:"))
        await self.vscroll.mount(Input(id="new-description", valid_empty=False))
        if stype == "Select" or stype == "Select_no_default":
            await self.vscroll.mount(Label("Select values (separate with ','):"))
            Validators = [ Function(self.val.is_valid_selection) ]
            await self.vscroll.mount(Input(id="new-select-values", validators=Validators,
                                           restrict=r"[0-9a-z_, ]*", valid_empty=False))
        await self.vscroll.mount(Button("Add", id=f"button-add-setting"))

    async def mount_settings_add_custom(self, stype) -> None:
        while not self.vscroll.children[-1].id == "custom-setting-select-add":
            await self.vscroll.children[-1].remove()
        if not stype == Select.BLANK:
            await self.mount_custom_setting_form(stype)

    async def edit_endpoint_add_custom(self) -> None:
        types = [ "Integer", "Float", "Boolean", "String", "Text", "Select", "Select_no_default" ]
        await self.vscroll.mount(Label("Add custom setting:"))
        await self.vscroll.mount(Select.from_values(types, id="custom-setting-select-add", allow_blank=False))

    async def edit_endpoint_remove_custom(self) -> None:
        names = []
        for setting, *others in self.settings.endpoints[self.cur_endpoint]["custom"]:
            if (not setting == "name" and
                not setting == "endpoint_url" and
                not setting == "key" and
                not setting == "reasoning_key"):
                names.append(setting)
        await self.vscroll.mount(Label("Remove custom setting:"))
        await self.vscroll.mount(Select.from_values(names, id="custom-setting-select-remove", allow_blank=False))
        await self.vscroll.mount(Button("Remove", id=f"button-remove-setting"))

    async def edit_endpoint(self) -> None:
        for setting, stype, desc, amore in self.settings.endpoints[self.cur_endpoint]["custom"]:
            id = setting.replace(".", "-")
            await self.vscroll.mount(Label(f"{desc}: ({stype})"))
            value = None
            if setting in self.settings.endpoints[self.cur_endpoint]["values"]:
                value = self.settings.endpoints[self.cur_endpoint]["values"][setting]
            if value is None:
                value = ""
            Validators = []
            vtype = "text"
            valid_empty = True
            if setting == "name":
                valid_empty = False
                Validators.append(Function(self.val.is_unique_name))
            elif setting == "endpoint_url":
                valid_empty = False
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
                await self.vscroll.mount(Select.from_values(amore, id=id, value=value, prompt="Default"))
            elif stype == "Select_no_default":
                if not value:
                    value = amore[0]
                await self.vscroll.mount(Select.from_values(amore, id=id, value=value, allow_blank=False))
            elif stype == "Boolean":
                await self.vscroll.mount(Switch(id=id, value=value))
            elif stype == "Text":
                await self.vscroll.mount(TextArea(value, id=id))
            else:
                await self.vscroll.mount(Input(type=vtype, validators=Validators, valid_empty=valid_empty,
                                               id=f"{setting}", value=value))

    async def edit_endpoint_screen(self) -> None:
        self.vscroll = VerticalScroll(id="edit-endpoint")
        await self.dyn_container.mount(self.vscroll)
        await self.edit_endpoint()
        await self.vscroll.mount(Rule())
        await self.edit_endpoint_remove_custom()
        await self.vscroll.mount(Rule())
        await self.edit_endpoint_add_custom()
        horiz = Horizontal(id="save-delete-cancel")
        await self.dyn_container.mount(horiz)
        await horiz.mount(Button("Save", id="save"))
        await horiz.mount(Button("Delete", id="delete"))
        await horiz.mount(Button("Set Active", id="set-active"))
        await horiz.mount(Button("Cancel", id="cancel"))
        self.vscroll.focus()

    async def select_endpoint_screen(self) -> None:
        self.vscroll = VerticalScroll(id="select-main")
        await self.dyn_container.mount(self.vscroll)
        Options = [ Option("\nCreate new endpoint\n", id="select-new-endpoint") ]
        for endpoint in self.settings.endpoints.keys():
            name=self.settings.endpoints[endpoint]["values"]["name"]
            Options.append(Option(f"\nEdit: {name}\n", id=f"select-endpoint-{endpoint}"))
        await self.vscroll.mount(OptionList(*Options, id="option-list"))
        horiz = Horizontal(id="cancel-container")
        await self.dyn_container.mount(horiz)
        await horiz.mount(Button("Cancel", id="cancel"))
        self.vscroll.children[0].focus()
