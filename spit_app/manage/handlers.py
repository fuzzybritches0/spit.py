from textual.widgets import OptionList, Button

class HandlersMixIn:
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
        if event.button.id == "cancel":
            await self.action_cancel()
        elif event.button.id == "delete":
            await self.action_delete()
        elif event.button.id == "save":
            await self.action_save()
        elif event.button.id == "duplicate":
            self.action_duplicate()
        elif hasattr(self, "on_button_pressed_extra"):
            await self.on_button_pressed_extra(event)
