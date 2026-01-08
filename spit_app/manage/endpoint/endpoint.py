from uuid import uuid4
from textual.containers import VerticalScroll
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn
from spit_app.manage.manage import Manage

class Endpoints(ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, VerticalScroll, Manage):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("escape", "cancel", "Cancel"),
        ("ctrl+t", "duplicate", "Duplicate")
    ]
    NEW = {
            "name": { "stype": "string", "empty": False, "desc": "Name"},
            "endpoint_url": { "stype": "url", "empty": False, "desc": "Endpoint URL",
                            "value": "http://127.0.0.1:8080" },
            "key": { "stype": "string", "desc": "API Access Key" },
            "reasoning_key": { "stype": "select_no_default", "desc": "Reasoning Key",
                            "options":["reasoning_content", "reasoning"] },
            "temperature": { "stype": "float", "empty": True, "desc": "Temperature" },
            "top_p": { "stype": "float", "desc": "TOP-P" },
            "min_p": { "stype": "float", "desc": "MIN-P" },
            "top_k": { "stype": "float", "desc": "TOP-K" }
    }

    def __init__(self) -> None:
        super().__init__()
        self.id = "manage-endpoints"
        self.classes = "manage"
        self.managed = self.app.settings.endpoints
        self.save_managed = self.app.settings.save_endpoints
        self.new_manage = False

    def add_custom_setting(self, setting: str, stype: str, desc: str, sarray: list = []) -> None:
        if not sarray:
            self.manage[setting] = { "stype": stype, "desc": desc }
        else:
            self.manage[setting] = { "stype": stype, "desc": desc , "options": sarray}

    def remove_custom_setting(self, setting: str) -> None:
        del self.manage[setting]
