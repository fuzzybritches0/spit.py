from copy import deepcopy
from uuid import uuid4
from textual.widgets import Select
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn

class Manage(ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn):
    def duplicate(self) -> None:
        self.new_manage = True
        self.uuid = str(uuid4())
        self.query_one("#name").value = self.uuid

    def new(self) -> None:
        self.new_manage = True
        self.uuid = str(uuid4())
        self.manage = self.NEW

    def load(self, uuid: str) -> None:
        self.new_manage = False
        self.uuid = uuid
        self.manage = deepcopy(self.managed[uuid])

    def store_values(self) -> None:
        for setting in self.manage.keys():
            id = setting.replace(".", "-")
            if self.manage[setting]["stype"] == "text":
                newvalue = self.query_one(f"#{id}").text
            else:
                newvalue = self.query_one(f"#{id}").value
            if newvalue == Select.BLANK:
                newvalue = ""
            self.store_value(setting, newvalue)

    def store_value(self, setting: str, value: str|bool) -> None:
        stype = self.manage[setting]["stype"]
        if (stype == "float" or stype == "ufloat") and value:
            value = float(value)
        elif (stype == "integer" or stype == "uinteger") and value:
            value = int(value)
        elif not stype == "boolean":
            value = value.strip()
        self.manage[setting]["value"] = value

    def save(self) -> None:
        self.managed[self.uuid] = deepcopy(self.manage)
        self.save_managed()

    def delete(self) -> None:
        del self.managed[self.uuid]
        self.save_managed()
