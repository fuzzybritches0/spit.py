class CallbacksMixIn:
    async def update_llamacpp_success(self) -> None:
        await self.query_one("#active_version").method_update_options()
        await self.query_one("#delete_version").method_update_options()
        if self.gets("active_version") in self.get_versions_list():
            self.query_one("#active_version").value = self.gets("active_version")

    async def update_llamacpp_failed(self) -> None:
        await self.update_input_llamacpp_version()

    async def download_model_success(self) -> None:
        self.update_models_select_list()
        await self.query_one("#download_model").method_update_options()
