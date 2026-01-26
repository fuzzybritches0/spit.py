from textual.widgets import Button, OptionList

class HandlersMixIn:
    def on_focus(self) -> None:
        if self.children:
            if self.children[0].id == "option-list":
                self.children[0].focus()
            elif len(self.children) > 0:
                self.children[1].focus()

    async def on_mount(self) -> None:
        if self.new_chat:
            await self.edit_chat()
        else:
            await self.select_main_screen()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "select-new-chat":
            await self.remove_children()
            await self.edit_chat()
        elif event.option.id == "select-archive":
            self.cur_dir = self.chats_archive
            await self.remove_children()
            await self.select_main_screen()
        elif event.option.id == "select-leave-archive":
            self.cur_dir = self.chats
            await self.remove_children()
            await self.select_main_screen()
        else:
            self.cur_chat = str(event.option.id)
            await self.remove_children()
            await self.edit_chat(self.cur_chat)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            await self.action_cancel()
        elif event.button.id == "delete":
            await self.action_delete()
        elif event.button.id == "archive":
            await self.action_archive()
        elif event.button.id == "unarchive":
            await self.action_unarchive()
        elif event.button.id == "save":
            await self.action_save()
