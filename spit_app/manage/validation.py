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

    def valid_url(self, value) -> tuple:
        if value:
            if value.startswith("http://"):
                return (True, None)
            if value.startswith("https://"):
                return (True, None)
            return (False, "Not a valid URL!")
        return (True, None)

    def valid_float(self, value: str) -> bool:
        return self.is_valid("float", True, value)

    def valid_ufloat(self, value: str) -> bool:
        return self.is_valid("float", False, value)

    def valid_integer(self, value: str) -> bool:
        return self.is_valid("integer", True, value)

    def valid_uinteger(self, value: str) -> bool:
        return self.is_valid("integer", False, value)

    def is_not_empty(self, value) -> tuple:
        if value:
            return (True, None)
        return (False, "Must not be empty!")

    def is_valid(self, stype: str, usign: bool, value: str) -> tuple:
        stypes = { "integer": int, "float": float }
        u = ""
        if usign:
            u = "u"
        if value:
            try:
                stypes[stype](value)
                if not usign:
                    if stypes[stype](value) < 0:
                        return (False, f"Not a valid {u}{stype}!")
                return (True, None)
            except ValueError:
                return (False, f"Not a valid {u}{stype}!")
        else:
            return (True, None)

    def is_valid_chars(self, value: str) -> tuple:
        chars=string.ascii_lowercase + string.digits + "_.-"
        for char in value:
            if not char in chars:
                return (False, f"{char} not allowed!")
        return (True, None)

    def is_valid_setting(self, value: str) -> tuple:
        if value:
            valid, failure = self.is_valid_chars(value)
            if not valid:
                return (False, failure)
            if value[0].isdecimal():
                return (False, "Must not start with decimal!")
            if value.startswith("_") or value.endswith("_"):
                return (False, "Must not start or end with `_`!")
            if value.startswith("-") or value.endswith("-"):
                return (False, "Must not start or end with `-`!")
            if value.startswith(".") or value.endswith("."):
                return (False, "Must not start or end with `.`!")
            return True
        else:
            return True

    def is_valid_selection(self, value: str) -> tuple:
        if value:
            values = value.split(",")
            cvalues = []
            for value in values:
                if not value:
                    return (False, "No empty selection!")
                if "." in value:
                    return (False, "Must not contain `.`!")
                valid, failure = self.is_valid_setting(value.strip())
                if not valid:
                    return (False, failure)
                if value in cvalues:
                    return (False, "All selections must be unique!")
                cvalues += [value]
            return (True, None)
        else:
            return (False, "No selections!")

    def validate_values_edit(self) -> bool:
        valid = True
        for setting in self.manage.keys():
            stype = self.manage[setting]["stype"]
            id = setting.replace(".", "-")
            if not stype == "boolean" and not stype.startswith("select") and not stype == "text":
                inp = self.query_one(f"#{id}")
                inp.validate(inp.value)
                if not inp.is_valid:
                    valid = False
            elif stype == "text":
                if "empty" in self.manage[setting] and not self.manage[setting]["empty"]:
                    if not self.query_one(f"#{id}").text:
                        self.query_one(f"#{id}").classes = "text-area-invalid"
                        valid = False
                if hasattr(self, f"valid_setting_{setting}"):
                    valid, failure = getattr(self, f"valid_setting_{setting}")(self.query_one(f"#{id}").text)
                    if not valid:
                        self.query_one(f"#{id}").classes = "text-area-invalid"
                        valid = False
        return valid
