# SPDX-License-Identifier: GPL-2.0

class ValidationMixIn:
    def valid_values_add(self) -> bool:
        if not self.query_one("#new-setting").is_valid:
            return False
        if not self.query_one("#new-description").is_valid:
            return False
        stype = self.query_one("#custom-setting-select-add").value
        if stype == "Select" or stype == "Select_no_default":
            if not self.query_one("#new-select-values").is_valid:
                return False
        return True

    def is_not_empty(self, value) -> bool:
        if value:
            return True
        return False

    def valid_values_edit(self) -> bool:
        for setting in self.endpoint.keys():
            stype = self.endpoint[setting]["stype"]
            id = setting.replace(".", "-")
            if (not stype == "boolean" and not stype == "select" and
                not stype == "select_no_default" and not stype == "text"):
                if not self.query_one(f"#{id}").is_valid:
                    return False
        return True

    def is_url(self, value) -> bool:
        if value.startswith("http://"):
            return True
        if value.startswith("https://"):
            return True
        return False
    
    def is_unique_name(self, value: str) -> bool:
        if not value:
            return False
        for endpoint in self.app.settings.endpoints.keys():
            if (not endpoint == self.uuid and
                    self.app.settings.endpoints[endpoint]["name"]["value"] == value):
                return False
        return True

    def is_unique_custom(self, value: str) -> bool:
        if not value:
            return False
        same = 0
        for name in self.app.settings.endpoints[self.uuid].keys():
            if name == value:
                return False
        return True

    def is_valid_setting(self, value: str) -> bool:
        value = value.strip()
        if not value:
            return False
        if value.startswith("_") or value.endswith("_"):
            return False
        if value.startswith(".") or value.endswith("."):
            return False
        if value[0:1].isdecimal():
            return False
        return True

    def is_valid_selection(self, value: str) -> bool:
        values = value.split(",")
        if len(values) < 1:
            return False
        for value in values:
            if not self.is_valid_setting(value):
                return False
        return True

    def is_valid_values_edit(self) -> bool:
        for setting in self.endpoint.keys():
            stype = self.endpoint[setting]["stype"]
            id = setting.replace(".", "-")
            if (not stype == "boolean" and not stype == "select" and
                not stype == "select_no_default" and not stype == "text"):
                inp = self.query_one(f"#{id}")
                inp.validate(inp.value)
                if not inp.is_valid:
                    return False
        return True

    def is_valid_add_setting(self) -> bool:
        setting = self.query_one("#new-setting")
        desc = self.query_one("#new-description")
        setting.validate(setting.value)
        desc.validate(desc.value)
        if not setting.is_valid:
            return False
        if not desc.is_valid:
            return False
        return True
