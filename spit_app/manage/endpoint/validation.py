# SPDX-License-Identifier: GPL-2.0

class ValidationMixIn:
    def valid_setting_name(self, value: str) -> tuple:
        valid = True
        if value:
            for manage in self.managed.keys():
                if not manage == self.uuid and self.managed[manage]["name"]["value"].strip() == value.strip():
                    valid = False
                    break
        if not valid:
            return (False, "Must be unique!")
        return (True, None)

    def is_unique_custom(self, value: str) -> tuple:
        valid = True
        if value:
            for name in self.manage.keys():
                if name.strip() == value.strip():
                    valid = False
                    break
        if not valid:
            return (False, "Must be unique!")
        return (True, None)

    def validate_add_setting(self) -> tuple:
        valid = True
        failed = []
        setting = self.query_one("#new-setting")
        desc = self.query_one("#new-description")
        sel = None
        if self.query_one("#custom-setting-select-add").value.startswith("select"):
            sel = self.query_one("#new-select-values")
            sel.validate(sel.value)
        setting.validate(setting.value)
        desc.validate(desc.value)
        if not setting.is_valid:
            valid = False
            failed += ["- `Setting`: valid: (a-z0-9_-), start with (a-z), end with (a-z0-9), be unique!"]
        if not desc.is_valid:
            valid = False
            failed += ["- `Description`: must not be empty!"]
        if sel:
            if not sel.is_valid:
                valid = False
                failed +=["- `Select values`: valid: (a-z0-9_-), start with (a-z), end with (a-z0-9), be unique!"]
        return (valid, failed)
