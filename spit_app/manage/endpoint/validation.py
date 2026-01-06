# SPDX-License-Identifier: GPL-2.0

class ValidationMixIn:
    def is_valid(self, stype: str, usign: bool, value) -> bool:
        stypes = { "integer": int, "float": float }
        if not isinstance(value, str) or not value.strip():
            return False
        try:
            stypes[stype](value)
            if not usign:
                if stypes[stype](value) < 0:
                    return False
            return True
        except ValueError:
            return False

    def valid_setting_name(self, value: str) -> bool:
        if not value:
            return False
        for endpoint in self.app.settings.endpoints.keys():
            if (not endpoint == self.uuid and
                    self.app.settings.endpoints[endpoint]["name"]["value"].strip() == value.strip()):
                return False
        return True

    def valid_url(self, value) -> bool:
        if value.startswith("http://"):
            return True
        if value.startswith("https://"):
            return True
        return False

    def valid_float(self, value: str) -> bool:
        return self.is_valid("float", True, value)

    def valid_ufloat(self, value: str) -> bool:
        return self.is_valid("float", False, value)

    def valid_integer(self, value: str) -> bool:
        return self.is_valid("integer", True, value)

    def valid_uinteger(self, value: str) -> bool:
        return self.is_valid("integer", False, value)

    def is_not_empty(self, value) -> bool:
        if value:
            return True
        return False

    def is_unique_custom(self, value: str) -> bool:
        if not value:
            return False
        same = 0
        for name in self.endpoint.keys():
            if name.strip() == value.strip():
                return False
        return True

    def is_valid_setting(self, value: str) -> bool:
        value = value.strip()
        if not value:
            return False
        if " " in value:
            return False
        if any(ch.isupper() for ch in value):
            return False
        if value[0].isdecimal():
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
        for value in values:
            if not self.is_valid_setting(value):
                return False
        return True

    def validate_values_edit(self) -> bool:
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

    def validate_add_setting(self) -> bool:
        setting = self.query_one("#new-setting")
        desc = self.query_one("#new-description")
        setting.validate(setting.value)
        desc.validate(desc.value)
        if not setting.is_valid:
            return False
        if not desc.is_valid:
            return False
        return True
