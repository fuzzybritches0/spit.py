# SPDX-License-Identifier: GPL-2.0
import inspect
from textual.widgets import OptionList, Button

class HandlersMixIn:
    def on_focus(self) -> None:
        if self.children:
            if self.children[0].id == "option-list":
                self.children[0].focus()
            elif len(self.children) > 0:
                self.children[1].focus()

    async def on_mount(self) -> None:
        await self.select_main_screen()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "select-new-manage":
            self.new()
            await self.remove_children()
            await self.edit_manage_screen()
        else: 
            self.load(event.option.id.split("-",2)[2])
            await self.remove_children()
            await self.edit_manage_screen()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        for binding, action, desc in self.BINDINGS:
            if action == event.button.id.replace("-", "_"):
                method = getattr(self, f"action_{action}")
                if inspect.iscoroutinefunction(method):
                    await method()
                else:
                    method()
                break
