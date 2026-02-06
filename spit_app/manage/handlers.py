# SPDX-License-Identifier: GPL-2.0
import inspect
from textual.widgets import OptionList, Button, Input, TextArea

class HandlersMixIn:
    def on_focus(self) -> None:
        if self.children:
            if self.children[0].id == "option-list":
                self.children[0].focus()
            elif len(self.children) > 0:
                self.children[1].focus()

    async def on_mount(self) -> None:
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
        content = ""
        if not event.validation_result.is_valid:
            vals = event.validation_result.failure_descriptions
            for val in vals:
                content += f"- {val}\n"
        await self.query_one(f"#val-{event.control.id}").update(content)

    async def on_text_area_changed(self, event: TextArea.Changed) -> None:
        content = ""
        id = event.control.id
        if "empty" in self.manage[self.fid(id)] and not self.manage[self.fid(id)]["empty"]:
            if not event.control.text:
                content += "- Must not be empty!\n"
        if hasattr(self, f"valid_setting_{id}"):
            valid, failed = getattr(self, f"valid_setting_{id}")(event.control.text)
            if failed:
                content += f"- {failed}"
        if content:
            self.query_one(f"#{id}").classes = "text-area-invalid"
        self.query_one(f"#val-{id}").update(content)
