from spit_app.manage.endpoint.common import Common, bindings, buttons
from spit_app.manage.endpoint.actions import ActionsMixIn
from spit_app.manage.endpoint.handlers import HandlersMixIn
from spit_app.manage.endpoint.screens import ScreensMixIn
from spit_app.manage.endpoint.validation import ValidationMixIn
from spit_app.manage.manage import Manage

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
        self.managed = self.app.settings.models
        self.save_managed = self.app.settings.save_models
