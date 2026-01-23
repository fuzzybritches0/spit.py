from spit_app.chat.chat import Chat

class ActionsMixIn:
    async def action_delete(self) -> None:
        self.delete()
        await self.remove_children()
        await self.select_main_screen()

    async def action_archive(self) -> None:
        self.archive()
        await self.remove_children()
        await self.select_main_screen()

    async def action_unarchive(self) -> None:
        self.unarchive()
        await self.remove_children()
        await self.select_main_screen()

    async def action_save(self) -> None:
        self.save()
        if not self.cur_chat:
            await self.app.query_one("#main").mount(Chat(self.uuid))
            await self.app.query_one("#side-panel").add_option_chat(self.uuid)
        await self.action_cancel()

    async def action_cancel(self) -> None:
        if self.new_chat:
            await self.remove()
        else:
            await self.remove_children()
            await self.select_main_screen()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.children and self.children[0].id == "option-list":
            return False
        elif action == "unarchive" and not self.archive_on:
            return False
        elif action == "archive" and not self.cur_chat:
            return False
        elif action == "delete" and not self.cur_chat:
            return False
        elif action == "save" and self.archive_on:
            return False
        return True
