from textual.widgets import Select
from .actions import ActionsMixIn as EndpointActions
from .handlers import HandlersMixIn as EndpointHandlers
from .screens import ScreensMixIn as EndpointScreens
from .validation import ValidationMixIn as EndpointValidations
from spit_app.manage.common import CommonMixIn

class Endpoints(EndpointActions, EndpointHandlers,
                EndpointScreens, EndpointValidations,
                CommonMixIn):
    CSS_PATH = "../../styles/manage.css"
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("ctrl+s", "set_active", "Set active"),
        ("escape", "dismiss", "Cancel")
    ]

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
