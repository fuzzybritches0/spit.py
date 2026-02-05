# SPDX-License-Identifier: GPL-2.0
import string
from textual.validation import Function

class ValidationMixIn:
    def validators(self, setting: str, id: str, stype: str) -> list:
        Validators = []
        if "empty" in self.manage[setting] and not self.manage[setting]["empty"]:
            Validators.append(Function(self.is_not_empty))
        if not stype == "text" and hasattr(self, f"valid_setting_{id}"):
            Validators.append(Function(getattr(self, f"valid_setting_{id}")))
        if hasattr(self, f"valid_{stype}"):
            Validators.append(Function(getattr(self, f"valid_{stype}")))
        return Validators

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

    def is_valid(self, stype: str, usign: bool, value: str) -> bool:
        stypes = { "integer": int, "float": float }
        if value:
            try:
                stypes[stype](value)
                if not usign:
                    if stypes[stype](value) < 0:
                        return False
                return True
            except ValueError:
                return False
        else:
            return True

    def is_valid_chars(self, value: str) -> bool:
        chars=string.ascii_lowercase + string.digits + "_.-"
        for char in value:
            if not char in chars:
                return False
        return True

    def is_valid_setting(self, value: str) -> bool:
        if value:
            if not self.is_valid_chars(value):
                return False
            if value[0].isdecimal():
                return False
            if value.startswith("_") or value.endswith("_"):
                return False
            if value.startswith("-") or value.endswith("-"):
                return False
            if value.startswith(".") or value.endswith("."):
                return False
            return True
        else:
            return True

    def is_valid_selection(self, value: str) -> bool:
        if value:
            values = value.split(",")
            cvalues = []
            for value in values:
                if not value or "." in value:
                    return False
                if not self.is_valid_setting(value.strip()):
                    return False
                if value in cvalues:
                    return False
                cvalues += [value]
            return True
        else:
            return False

    def validate_values_edit(self) -> bool:
        valid = True
        for setting in self.manage.keys():
            stype = self.manage[setting]["stype"]
            id = setting.replace(".", "-")
            if not stype == "boolean" and not stype.startswith("select") and not stype == "text":
                inp = self.query_one(f"#{id}")
                inp.validate(inp.value)
                if inp.is_valid and valid:
                    valid = True
                else:
                    valid = False
            if stype == "text" and "empty" in self.manage[setting] and not self.manage[setting]["empty"]:
                if not self.query_one(f"#{id}").text:
                    self.query_one(f"#{id}").classes = "text-area-invalid"
                    return False
        return valid
