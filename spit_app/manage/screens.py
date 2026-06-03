# SPDX-License-Identifier: GPL-2.0
import inspect
from textual.containers import Horizontal
from textual.widgets import OptionList, Button, Input, TextArea, Switch, Label, Select, SelectionList, Markdown
from textual.widgets.option_list import Option
from .input_widget import InputWidget

class ScreensMixIn:
    def extra_options(self) -> list:
        name = self.id.split("-", 1)
        name = name[1].replace("-", " ")
        return [Option(f"\nCreate new {name}\n", id="select-new-manage")]

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

    async def edit_manage(self) -> None:
        input_widget = InputWidget(self.manage, self.validators)
        for setting in self.manage.keys():
            await self.mount_all(await input_widget.setting(setting), before="#save-delete-cancel")
