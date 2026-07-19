class CallbacksMixIn:
    async def update_llamacpp_success(self) -> None:
        await self.query_one("#active_version").method_update_options()
        await self.query_one("#delete_version").method_update_options()

    async def update_llamacpp_failed(self) -> None:
        await self.update_input_llamacpp_version()

    async def download_model_success(self) -> None:
        await self.query_one("#active_model").method_update_options()
        await self.query_one("#download_model").method_update_options()
