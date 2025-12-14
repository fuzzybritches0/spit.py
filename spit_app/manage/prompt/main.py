from textual.widgets import Select
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn
from spit_app.manage.common import CommonMixIn

class Prompts(ActionsMixIn, HandlersMixIn,
              ScreensMixIn, ValidationMixIn,
              CommonMixIn):
    CSS_PATH = "../../styles/manage.css"
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("escape", "dismiss", "Cancel")
    ]

    def store_values(self) -> None:
        name = self.query_one("#name").value
        text = self.query_one("#text").text
        self.settings.system_prompts[self.cur_system_prompt] = {
                "name": name,
                "text": text
        }
