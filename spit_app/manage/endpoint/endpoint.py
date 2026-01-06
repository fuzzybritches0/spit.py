from uuid import uuid4
from copy import deepcopy
from textual.widgets import Select
from textual.containers import VerticalScroll
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn

class Endpoints(ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, VerticalScroll):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("ctrl+t", "duplicate", "Duplicate"),
        ("escape", "cancel", "Cancel")
    ]

    def __init__(self) -> None:
        super().__init__()
        self.settings = self.app.settings
        self.id = "manage-endpoints"
        self.classes = "manage"
        self.new_endpoint = False

    def duplicate(self) -> None:
        self.new_endpoint = True
        self.uuid = str(uuid4())
        self.query_one("#name").value = self.uuid

    def new(self) -> None:
        self.new_endpoint = True
        self.uuid = str(uuid4())
        self.endpoint = {
            "name": { "stype": "string", "empty": False, "desc": "Name", "value": self.uuid },
            "endpoint_url": { "stype": "url", "empty": False, "desc": "Endpoint URL",
                            "value": "http://127.0.0.1:8080" },
            "key": { "stype": "string", "empty": True, "desc": "API Access Key" },
            "reasoning_key": { "stype": "select_no_default", "desc": "Reasoning Key",
                            "options":["reasoning_content", "reasoning"] },
            "temperature": { "stype": "float", "empty": True, "desc": "Temperature" },
            "top_p": { "stype": "float", "empty": True, "desc": "TOP-P" },
            "min_p": { "stype": "float", "empty": True, "desc": "MIN-P" },
            "top_k": { "stype": "float", "empty": True, "desc": "TOP-K" }
        }

    def load(self, uuid: str) -> None:
        self.new_endpoint = False
        self.uuid = uuid
        self.endpoint = deepcopy(self.settings.endpoints[uuid])

    def store_values(self) -> None:
        for setting in self.endpoint.keys():
            id = setting.replace(".", "-")
            if self.endpoint[setting]["stype"] == "text":
                newvalue = self.query_one(f"#{id}").text
            else:
                newvalue = self.query_one(f"#{id}").value
            if newvalue == Select.BLANK:
                newvalue = ""
            self.store_value(setting, newvalue)

    def store_value(self, setting: str, value: str|bool) -> None:
        stype = self.endpoint[setting]["stype"]
        if (stype == "float" or stype == "ufloat") and value:
            value = float(value)
        elif (stype == "integer" or stype == "uinteger") and value:
            value = int(value)
        else:
            value = value.strip()
        self.endpoint[setting]["value"] = value

    def save(self) -> None:
        self.settings.endpoints[self.uuid] = deepcopy(self.endpoint)
        self.settings.save_endpoints()

    def delete(self) -> None:
        del self.settings.endpoints[self.uuid]
        self.settings.save_endpoints()

    def add_custom_setting(self, setting: str, stype: str, desc: str, sarray: list = []) -> None:
        if not sarray:
            self.endpoint[setting] = { "stype": stype, "empty": True, "desc": desc }
        else:
            self.endpoint[setting] = { "stype": stype, "desc": desc , "options": sarray}

    def remove_custom_setting(self, rsetting: str) -> None:
        del self.endpoint[rsetting]
