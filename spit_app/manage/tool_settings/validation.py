from textual.validation import Function

class ValidationMixIn:
    def validators(self, setting: str, id: str, stype: str) -> list:
        if "validators" in self.app.tool_call.tools[self.uuid]:
            validators = self.app.tool_call.tools[self.uuid]["validators"]
            if hasattr(validators, setting):
                setattr(self, f"valid_setting_{setting}", getattr(validators, setting))
        return super().validators(setting, id, stype)
