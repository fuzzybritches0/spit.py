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
        ("ctrl+d", "duplicate", "Duplicate"),
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
            "values": {"name": self.uuid,
                       "endpoint_url": "http://127.0.0.1:8080"},
            "custom": [
                ("name", "String", "Name", []),
                ("endpoint_url", "String", "Endpoint URL", []),
                ("key", "String", "API Access Key", []),
                ("reasoning_key", "Select_no_default", "Reasoning Key", ["reasoning_content", "reasoning"]),
                ("temperature", "Float", "Temperature", []),
                ("top_p", "Float", "TOP-P", []),
                ("min_p", "Float", "MIN-P", []),
                ("top_k", "Float", "TOP-K", [])
            ]
        }

    def load(self, uuid: str) -> None:
        self.new_endpoint = False
        self.uuid = uuid
        self.endpoint = deepcopy(self.settings.endpoints[uuid])

    def store_values(self) -> None:
        for setting, stype, desc, array in self.endpoint["custom"]:
            id = setting.replace(".", "-")
            if stype == "Text":
                newvalue = self.query_one(f"#{id}").text
            else:
                newvalue = self.query_one(f"#{id}").value
            if newvalue == Select.BLANK:
                newvalue = ""
            self.store_value(setting, stype, newvalue)

    def store_value(self, setting: str, stype: str, value: str|bool) -> None:
        if stype == "Float" and value:
            value = float(value)
        elif stype == "Integer" and value:
            value = int(value)
        self.endpoint["values"][setting] = value

    def save(self) -> None:
        self.settings.endpoints[self.uuid] = deepcopy(self.endpoint)
        self.settings.save_endpoints()

    def delete(self) -> None:
        del self.settings.endpoints[self.uuid]
        self.settings.save_endpoints()

    def add_custom_setting(self, setting: str, stype: str, desc: str, sarray: list) -> None:
        self.endpoint["custom"].append((setting, stype, desc, sarray))

    def remove_custom_setting(self, rsetting: str) -> None:
        custom = []
        values = {}
        for setting, stype, desc, sarray in self.endpoint["custom"]:
            if not rsetting == setting:
                custom.append((setting, stype, desc, sarray))
                if setting in self.endpoint["values"]:
                    values[setting] = self.endpoint["values"][setting]
        self.endpoint["custom"] = custom
        self.endpoint["values"] = values
