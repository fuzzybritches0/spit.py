from copy import deepcopy
from time import time
from textual.widgets import Select
from textual.containers import VerticalScroll
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn

class Manage(VerticalScroll, ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn):
    def __init__(self, id: str, new_manage: bool = False) -> None:
        super().__init__()
        if new_manage:
            self.id = f"new-{id}"
            self.new()
        else:
            self.id = f"manage-{id}"
        self.classes = "manage"
        self.settings = self.app.settings
        self.path = self.app.settings.path
        self.new_manage = new_manage

    def duplicate(self) -> None:
        self.new_manage = True
        self.uuid = str(time()).replace(".", "-")
        self.query_one("#name").value = self.query_one("#name").value + " duplicate"

    def new(self) -> None:
        self.new_manage = True
        self.uuid = str(time()).replace(".", "-")
        self.manage = deepcopy(self.NEW)

    def load(self, uuid: str) -> None:
        self.new_manage = False
        self.uuid = uuid
        self.manage = deepcopy(self.managed[uuid])

    def store_values(self) -> None:
        for setting in self.manage.keys():
            id = setting.replace(".", "-")
            if self.manage[setting]["stype"] == "text":
                newvalue = self.query_one(f"#{id}").text
            elif self.manage[setting]["stype"] == "select_list":
                newvalue = self.query_one(f"#{id}").selected
            else:
                newvalue = self.query_one(f"#{id}").value
            if newvalue == Select.BLANK:
                newvalue = ""
            self.store_value(setting, newvalue)

    def store_value(self, setting: str, value: str|bool|list) -> None:
        stype = self.manage[setting]["stype"]
        if (stype == "float" or stype == "ufloat") and value:
            value = float(value)
        elif (stype == "integer" or stype == "uinteger") and value:
            value = int(value)
        elif not stype == "boolean" and not stype.startswith("select"):
            value = value.strip()
        self.manage[setting]["value"] = value

    def save(self) -> None:
        if self.managed:
            self.managed[self.uuid] = deepcopy(self.manage)
        self.save_managed()

    def delete(self) -> None:
        del self.managed[self.uuid]
        self.save_managed()
