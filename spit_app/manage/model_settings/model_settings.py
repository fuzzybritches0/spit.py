from copy import deepcopy
from spit_app.manage.endpoint.common import Common, bindings, buttons
from spit_app.manage.endpoint.actions import ActionsMixIn
from spit_app.manage.endpoint.handlers import HandlersMixIn
from spit_app.manage.endpoint.screens import ScreensMixIn
from spit_app.manage.endpoint.validation import ValidationMixIn
from spit_app.manage.manage import Manage
from spit_app.llamacpp.models import MODELS_SETTINGS

class ModelSettings(Common, ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, Manage):
    NEW = {
            "name": { "stype": "string", "empty": False, "desc": "Name"},
            "temperature": { "stype": "float", "desc": "Temperature" },
            "top_p": { "stype": "float", "desc": "TOP-P" },
            "min_p": { "stype": "float", "desc": "MIN-P" },
            "top_k": { "stype": "float", "desc": "TOP-K" }
    }

    BINDINGS = bindings + [("ctrl+s", "reset", "Reset")]
    BUTTONS = buttons + (("reset", "Reset"),)

    def __init__(self) -> None:
        super().__init__("model-settings")
        self.managed = self.settings.models
        self.save_managed = self.settings.save_models
        self.load_managed = self.settings.load_models

    def custom_options(self) -> list:
        options = []
        for setting in self.manage.keys():
            if not setting == "name":
                options.append((setting, setting))
        return options

    async def action_reset(self) -> None:
        del self.managed[self.uuid]
        self.save_managed()
        self.load_managed()
        self.managed = self.settings.models
        self.manage = deepcopy(self.managed[self.uuid])
        await self.remove_children()
        await self.edit_manage_screen()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool|None:
        if self.children and self.children[0].id == "option-list":
            return False
        if action == "reset":
            if not self.uuid in MODELS_SETTINGS:
                return False
        if action == "delete":
            if self.uuid in MODELS_SETTINGS:
                return False
        if not action == "cancel" and not action == "save" and self.new_manage:
            return False
        return True

    def valid_setting_name(self, value: str) -> tuple:
        if value:
            for manage_id in self.managed.keys():
                manage = self.managed[manage_id]
                if not manage_id == self.uuid and manage["name"]["value"].strip() == value.strip():
                    return (False, "Must be unique!")
        return (True, None)
