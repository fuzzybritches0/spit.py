import os
import json
from datetime import datetime
from textual.widgets import Button, OptionList
from textual.widgets.option_list import Option

class HandlersMixIn:
    async def on_mount(self) -> None:
        if self.new_chat:
            await self.edit_chat()
        else:
            await self.select_main_screen()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            await self.action_cancel()
        elif event.button.id == "delete":
            await self.action_delete()
        elif event.button.id == "save":
            await self.action_save()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "select-new-chat":
            await self.remove_children()
            await self.edit_chat()
        else:
            self.cur_chat = str(event.option.id)
            await self.remove_children()
            await self.edit_chat(self.cur_chat)
