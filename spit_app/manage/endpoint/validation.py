# SPDX-License-Identifier: GPL-2.0

class ValidationMixIn:
    def valid_setting_name(self, value: str) -> bool:
        if not value:
            return False
        for manage in self.managed.keys():
            if (not manage == self.uuid and
                    self.managed[manage]["name"]["value"].strip() == value.strip()):
                return False
        return True

    def is_unique_custom(self, value: str) -> bool:
        if value:
            for name in self.manage.keys():
                if name.strip() == value.strip():
                    return False
            return True
        else:
            return True

    def validate_add_setting(self) -> bool:
        setting = self.query_one("#new-setting")
        desc = self.query_one("#new-description")
        sel = None
        if self.query_one("#custom-setting-select-add").value.startswith("select"):
            sel = self.query_one("#new-select-values")
            sel.validate(sel.value)
        setting.validate(setting.value)
        desc.validate(desc.value)
        if not setting.is_valid:
            return False
        if not desc.is_valid:
            return False
        if sel:
            if not sel.is_valid:
                return False
        return True
