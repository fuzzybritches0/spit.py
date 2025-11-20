# SPDX-License-Identifier: GPL-2.0
from textual.validation import Function
from textual.widgets import Input, Label, Button, OptionList
from textual.widgets.option_list import Option
from textual.containers import VerticalScroll, Horizontal, Container

async def edit_settings(self, vscroll):
    for setting, stype, desc, defvalue, *validators in self.settings:
        await vscroll.mount(Label(f"{desc} ({defvalue}):"))
        value = None
        if setting in self.config.config["configs"][self.cconfig]:
            value = self.config.config["configs"][self.cconfig][setting]
        if value == None:
            value = defvalue
        Validators = []
        for validator in validators:
            if stype == float or stype == int:
                value=str(value)
            Validators.append(Function(validator))
        await vscroll.mount(Input(validators=Validators, id=f"{setting}", value=value))

async def edit_settings_screen(self) -> None:
    vscroll = VerticalScroll(id="EditSettings")
    await self.dyn_container.mount(vscroll)
    await edit_settings(self, vscroll)
    horiz = Horizontal(id="SaveDeleteCancel")
    await self.dyn_container.mount(horiz)
    await horiz.mount(Button("Save", id="save"))
    await horiz.mount(Button("Delete", id="delete"))
    await horiz.mount(Button("Set Active", id="set_active"))
    await horiz.mount(Button("Cancel", id="cancel"))

async def select_config_screen(self) -> None:
    vscroll = VerticalScroll(id="SelectConfig")
    await self.dyn_container.mount(vscroll)
    Options = [ Option("\nCreate new config\n", id="select_new_config") ]
    count=0
    for configs in self.config.config["configs"]:
        name=self.config.config["configs"][count]["name"]
        Options.append(Option(f"\nEdit: {name}\n", id=f"select_config_{count}"))
        count+=1
    await vscroll.mount(OptionList(*Options, id="OptionList"))
    horiz = Horizontal(id="Cancel")
    await self.dyn_container.mount(horiz)
    await horiz.mount(Button("Cancel", id="cancel"))
    vscroll.children[0].focus()

async def clean_dyn_container(self) -> None:
    await self.dyn_container.remove_children()
