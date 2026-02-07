# SPDX-License-Identifier: GPL-2.0
from textual.containers import Horizontal
from textual.widgets import OptionList, Button, Input, TextArea, Switch, Label, Select, SelectionList, Markdown
from textual.widgets.option_list import Option

class ScreensMixIn:
    def extra_options(self) -> list:
        return [Option(f"\nCreate new {self.id.split("-")[1]}\n", id="select-new-manage")]

    def get_name(self, manage: str) -> str:
        return self.managed[manage]["name"]["value"]

    async def select_main_screen(self) -> None:
        Options = self.extra_options()
        if hasattr(self, "get_managed"):
            self.managed = self.get_managed()
        for manage in self.managed.keys():
            name = self.get_name(manage)
            Options.append(Option(f"\nEdit: {name}\n", id=f"select-manage-{manage}"))
        await self.mount(OptionList(*Options, id="option-list"))
        self.children[0].focus()

    def check_buttons(self) -> list:
        buttons = []
        for action, button in self.BUTTONS:
            if self.check_action(action, ()):
                buttons.append(Button(button, id=action))
        return buttons

    async def edit_manage_screen(self) -> None:
        await self.mount(Horizontal(*self.check_buttons(), id="save-delete-cancel"))
        await self.edit_manage()
        self.children[1].focus()

    async def mount_setting(self, setting: str, stype: str, desc: str, options: list) -> None:
        id = self.rid(setting)
        await self.mount(Label(f"{desc}: ({stype})", id="label-"+id), before="#save-delete-cancel")
        value = ""
        if "value" in self.manage[setting]:
            value = self.manage[setting]["value"]
        if "ameth" in self.manage[setting]:
            ameth = getattr(self, self.manage[setting]["ameth"])
            tup = ameth()
        elif options:
            tup = ()
            for el in options:
                tup += ((el, el),)
        Validators = self.validators(setting, id, stype)
        if stype == "integer" or stype == "uinteger" or stype == "float" or stype == "ufloat":
            value=str(value)
        if stype == "select":
            if not value or not value in (i for n, i in tup):
                value = Select.BLANK
            await self.mount(Select(tup, id=id, value=value,
                                                prompt="Default"), before="#save-delete-cancel")
        elif stype == "select_no_default":
            if not value or not value in (i for n, i in tup):
                value = tup[0][1]
            await self.mount(Select(tup, id=id, value=value, allow_blank=False), before="#save-delete-cancel")
        elif stype == "select_list":
            if not value:
                value = []
            ltup = ()
            for n, i in tup:
                if n in value:
                    ltup += ((n, i, True),)
                else:
                    ltup += ((n, i, False),)
            await self.mount(SelectionList(*ltup, id=id), before="#save-delete-cancel")
        elif stype == "boolean":
            await self.mount(Switch(id=id, value=value), before="#save-delete-cancel")
        elif stype == "text":
            await self.mount(TextArea(value, id=id, classes="text-area"), before="#save-delete-cancel")
        else:
            await self.mount(Input(validators=Validators, id=id, value=value), before="#save-delete-cancel")
        if not "select" in stype or not stype == "boolean":
            await self.mount(Markdown(id=f"val-{id}"), before="#save-delete-cancel")

    async def edit_manage(self) -> None:
        for setting in self.manage.keys():
            options = []
            if "options" in self.manage[setting]:
                options = self.manage[setting]["options"]
            await self.mount_setting(setting, self.manage[setting]["stype"],
                                     self.manage[setting]["desc"], options)
