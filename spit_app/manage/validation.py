# SPDX-License-Identifier: GPL-2.0
import string
from textual.validation import Validator, ValidationResult


class Function(Validator):
    def __init__(self, function: callable) -> None:
        self.function = function
        self.failure_description = None

    def validate(self, value: str) -> ValidationResult:
        valid, failure = self.function(value)
        if valid:
            return self.success()
        else:
            return self.failure(failure)

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

    failed_valid_url = ["Not a valid URL"]
    def valid_url(self, value) -> bool:
        if value.startswith("http://"):
            return True
        if value.startswith("https://"):
            return True
        return False

    failed_valid_float = ["Not a valid float"]
    def valid_float(self, value: str) -> bool:
        return self.is_valid("float", True, value)

    failed_valid_ufloat = ["Not a valid ufloat"]
    def valid_ufloat(self, value: str) -> bool:
        return self.is_valid("float", False, value)

    failed_valid_integer = ["Not a valid integer"]
    def valid_integer(self, value: str) -> bool:
        return self.is_valid("integer", True, value)

    failed_valid_uinteger = ["Not a valid uinteger"]
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

    def get_failed_val_info(self, stype: str, setting: str) -> str:
        ret = []
        if hasattr(self, f"failed_valid_{stype}"):
            ret.append(f"- `{setting}`: " + getattr(self, f"failed_valid_{stype}")[0])
        if hasattr(self, f"failed_valid_setting_{setting}"):
            ret.append(f"- `{setting}`: " + getattr(self, f"failed_valid_setting_{setting}")[0])
        if not ret:
            return [f"- `{setting}`: not valid!"]
        return ret

    def validate_values_edit(self) -> tuple[bool, list]:
        valid = True
        failed = []
        for setting in self.manage.keys():
            stype = self.manage[setting]["stype"]
            id = setting.replace(".", "-")
            if not stype == "boolean" and not stype.startswith("select") and not stype == "text":
                inp = self.query_one(f"#{id}")
                inp.validate(inp.value)
                if not inp.is_valid:
                    if "empty" in self.manage[setting] and not self.manage[setting]["empty"]:
                        if not self.query_one(f"#{id}").value:
                            failed += [f"- `{setting}` must not be empty!"]
                    failed += self.get_failed_val_info(stype, setting)
                    valid = False
            if stype == "text":
                if "empty" in self.manage[setting] and not self.manage[setting]["empty"]:
                    if not self.query_one(f"#{id}").text:
                        self.query_one(f"#{id}").classes = "text-area-invalid"
                        failed += [f"- `{setting}` must not be empty!"]
                        valid = False
                if hasattr(self, f"valid_setting_{setting}"):
                    if not getattr(self, f"valid_setting_{setting}")(self.query_one(f"#{id}").text):
                        self.query_one(f"#{id}").classes = "text-area-invalid"
                        failed += self.get_failed_val_info(stype, setting)
                        valid = False
        return (valid, failed)
