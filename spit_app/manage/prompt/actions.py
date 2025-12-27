class ActionsMixIn:
    async def action_delete(self) -> None:
        self.settings.delete_system_prompt(self.cur_system_prompt)
        await self.remove_children()
        await self.select_main_screen()

    async def action_save(self) -> None:
        if self.valid_values_edit():
            self.store_values()
            self.settings.save_system_prompts()
            await self.remove_children()
            await self.select_main_screen()

    async def action_cancel(self) -> None:
        await self.remove_children()
        await self.select_main_screen()

    def is_edit_prompt(self) -> bool:
        if self.children and self.children[0].id == "edit-prompt":
            return True
        return False

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "cancel" or action == "save" or action == "delete":
            return self.is_edit_prompt()
        return True
