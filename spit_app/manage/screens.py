# SPDX-License-Identifier: GPL-2.0
from textual.containers import Horizontal
from textual.widgets import OptionList, Button, Input, TextArea, Switch, Label, Select
from textual.widgets.option_list import Option

class ScreensMixIn:
    async def select_main_screen(self) -> None:
        Options = [ Option(f"\nCreate new {self.id.split("-")[1]}\n", id="select-new-manage") ]
        for manage in self.managed.keys():
            name=self.managed[manage]["name"]["value"]
            Options.append(Option(f"\nEdit: {name}\n", id=f"select-manage-{manage}"))
        await self.mount(OptionList(*Options, id="option-list"))
        self.children[0].focus()

    async def edit_manage_screen(self) -> None:
        await self.edit_manage()
        self.children[1].focus()
        if self.new_manage:
            buttons = [Button(desc, id=id) for id, desc in self.BUTTONS_NEW]
        else:
            buttons = [Button(desc, id=id) for id, desc in self.BUTTONS]
        await self.mount(Horizontal(*buttons, id="save-delete-cancel"))

    async def mount_setting(self, setting: str, stype: str, desc: str, amore: list, add: bool = False) -> None:
        id = setting.replace(".", "-")
        if add:
            await self.mount(Label(f"{desc}: ({stype})", id="label-"+id), before="#save-delete-cancel")
        else:
            await self.mount(Label(f"{desc}: ({stype})", id="label-"+id))
        value = ""
        if "value" in self.manage[setting]:
            value = self.manage[setting]["value"]
        Validators = self.validators(setting, id, stype)
        if stype == "integer" or stype == "uinteger" or stype == "float" or stype == "ufloat":
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
                await self.mount(Input(validators=Validators, id=id,
                                       value=value), before="#save-delete-cancel")
            else:
                await self.mount(Input(validators=Validators, id=id, value=value))

    async def edit_manage(self) -> None:
        for setting in self.manage.keys():
            options = []
            if "options" in self.manage[setting]:
                options = self.manage[setting]["options"]
            await self.mount_setting(setting, self.manage[setting]["stype"],
                                     self.manage[setting]["desc"], options)
