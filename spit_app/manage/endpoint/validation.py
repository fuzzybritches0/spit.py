# SPDX-License-Identifier: GPL-2.0

class ValidationMixIn:
    def valid_setting_name(self, value: str) -> tuple:
        if value:
            if value == self.app.server.name:
                return (False, "Must be unique!")
            for manage in self.app.endpoint_list():
                endpoint = self.app.get_endpoint(manage)
                if not manage == self.uuid and endpoint["name"]["value"].strip() == value.strip():
                    return (False, "Must be unique!")
        return (True, None)

    def is_unique_custom(self, value: str) -> tuple:
        if value:
            for name in self.manage.keys():
                if name.strip() == value.strip():
                    return (False, "Must be unique!")
        return (True, None)

    async def validate_add_setting(self) -> bool:
        setting = self.query_one("#new-setting")
        desc = self.query_one("#new-description")
        sel = None
        if self.query_one("#custom-setting-select-add").value.startswith("select"):
            sel = self.query_one("#new-select-values")
            val_result = sel.validate(sel.value)
            await self.update_val_results_input("new-select-values", val_result.failure_descriptions)
        val_result = setting.validate(setting.value)
        await self.update_val_results_input("new-setting", val_result.failure_descriptions)
        val_result = desc.validate(desc.value)
        await self.update_val_results_input("new-description", val_result.failure_descriptions)
        if not setting.is_valid:
            return False
        if not desc.is_valid:
            return False
        if sel:
            if not sel.is_valid:
                return False
        return True
