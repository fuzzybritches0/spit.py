class ActionsMixIn:
    async def action_delete(self) -> None:
        self.settings.delete_system_prompt(self.cur_system_prompt)
        self.app.title_update()
        await self.clean_dyn_container()
        await self.select_main_screen()

    async def action_save(self) -> None:
        if self.valid_values_edit():
            self.store_values()
            self.settings.save_system_prompts()
            self.app.title_update()
            await self.clean_dyn_container()
            await self.select_main_screen()

    async def action_dismiss(self) -> None:
        if self.dyn_container.children[0].id == "select-main":
            self.dismiss()
        else:
            await self.clean_dyn_container()
            await self.select_main_screen()
