from textual.widgets import Button, OptionList

class HandlersMixIn:
    async def on_mount(self) -> None:
        await self.select_main_screen()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            await self.remove_children()
            await self.select_main_screen()
        elif event.button.id == "delete":
            await self.action_delete()
        elif event.button.id == "save":
            await self.action_save()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "select-new-prompt":
            self.cur_system_prompt = self.settings.new_system_prompt()
            await self.remove_children()
            await self.edit_prompt_screen()
        else:
            self.cur_system_prompt = str(event.option.id[14:])
            await self.remove_children()
            await self.edit_prompt_screen()
