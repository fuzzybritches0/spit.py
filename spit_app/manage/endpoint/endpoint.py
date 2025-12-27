from textual.widgets import Select
from textual.containers import VerticalScroll
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn
from spit_app.manage.validation import Validation

class Endpoints(ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, VerticalScroll):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("escape", "cancel", "Cancel")
    ]

    def __init__(self) -> None:
        super().__init__()
        self.settings = self.app.settings
        self.id = "manage-endpoints"
        self.classes = "manage"
        self.val = Validation(self)

    def store_values(self) -> None:
        for setting, stype, desc, array in self.settings.endpoints[self.cur_endpoint]["custom"]:
            id = setting.replace(".", "-")
            if stype == "Text":
                newvalue = self.query_one(f"#{id}").text
            else:
                newvalue = self.query_one(f"#{id}").value
            if newvalue == Select.BLANK:
                newvalue = ""
            self.settings.store(self.cur_endpoint, setting, stype, newvalue)
