import inspect
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

    def avail_buttons(self) -> tuple:
        return (
            ("cancel", self.action_cancel),
            ("delete", self.action_delete),
            ("save", self.action_save),
            ("duplicate", self.action_duplicate)
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        for button, action in self.avail_buttons():
            if button == event.button.id:
                if inspect.iscoroutinefunction(action):
                    await action()
                else:
                    action()
                break
