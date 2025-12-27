from textual.containers import Vertical
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn
from spit_app.manage.validation import Validation

class Chat(ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, Vertical):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("escape", "cancel", "Cancel")
    ]

    def __init__(self) -> None:
        super().__init__()
        self.settings = self.app.settings
        self.id = "manage-chats"
        self.classes = "manage"
        self.cur_chat = None
        self.val = Validation(self)
