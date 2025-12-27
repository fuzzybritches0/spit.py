from textual.containers import Vertical
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn
from spit_app.manage.validation import Validation

class Prompts(ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, Vertical):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("escape", "cancel", "Cancel")
    ]

    def __init__(self) -> None:
        super().__init__()
        self.settings = self.app.settings
        self.id = "manage-prompts"
        self.classes = "manage"
        self.val = Validation(self)

    def store_values(self) -> None:
        name = self.query_one("#name").value
        text = self.query_one("#text").text
        self.settings.system_prompts[self.cur_system_prompt] = {
                "name": name,
                "text": text
        }
