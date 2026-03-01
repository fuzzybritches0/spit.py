# SPDX-License-Identifier: GPL-2.0
import inspect
from textual.widgets import OptionList, Button, Input, TextArea

class HandlersMixIn:
    def on_focus(self) -> None:
        if self.children:
            if self.focused_el:
                self.focused_el.focus(scroll_visible=False)
            elif self.children[0].id == "option-list":
                self.children[0].focus()
            elif len(self.children) > 0:
                self.children[1].focus()

    def on_descendant_focus(self) -> None:
        self.focused_el = self.app.focused

    async def on_mount(self) -> None:
        self.app.focused_container = self
        if self.new_manage and hasattr(self, "manage"):
            await self.edit_manage_screen()
        else:
            await self.select_main_screen()

    async def on_extra_options(self, id) -> bool:
        return False

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if await self.on_extra_options(event.option.id):
            return None
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

    async def on_input_changed(self, event: Input.Changed) -> None:
        await self.update_val_results_input(event.control.id, event.validation_result.failure_descriptions)

    async def on_text_area_changed(self, event: TextArea.Changed) -> None:
        id = event.control.id
        await self.update_val_results_text(id, self.fid(id), event.control.text)
