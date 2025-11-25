# SPDX-License-Identifier: GPL-2.0
class Validation:
    def __init__(self, app) -> None:
        self.app = app

    def is_empty(self, value) -> bool:
        if value:
            return False
        return True

    def is_url(self, value) -> bool:
        if value.startswith("http://"):
            return True
        if value.startswith("https://"):
            return True
        return False
    
    def is_unique_name(self, value: str) -> bool:
        if self.is_empty(value):
            return False
        count = 0
        for config in self.app.config.endpoints:
            if (not count == self.app.cur_endpoint and
                    config["values"]["name"] == value):
                return False
            count+=1
        return True

    def is_unique_custom(self, value: str) -> bool:
        if self.is_empty(value):
            return False
        same = 0
        for name, stype, desc, sarray in self.app.config.endpoints[self.app.cur_endpoint]["custom"]:
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
