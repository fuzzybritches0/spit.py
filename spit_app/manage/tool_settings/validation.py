from textual.validation import Function

class ValidationMixIn:
    def validators(self, setting: str, id: str, stype: str) -> list:
        Validators = super().validators(setting, id, stype)
        if "validators" in self.app.tool_call.tools[self.uuid]:
            validators = self.app.tool_call.tools[self.uuid]["validators"]
            if hasattr(validators, setting):
                Validators.append(Function(getattr(validators, setting)))
        return Validators
