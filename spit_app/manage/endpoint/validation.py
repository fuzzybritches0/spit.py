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

    def valid_values_edit(self) -> bool:
        for setting, stype, desc, array in self.settings.endpoints[self.cur_endpoint]["custom"]:
            id = setting.replace(".", "-")
            if (not stype == "Boolean" and not stype == "Select" and
                not stype == "Select_no_default" and not stype == "Text"):
                if not self.query_one(f"#{id}").is_valid:
                    return False
        return True
