from uuid import uuid4
from copy import deepcopy
from textual.containers import Vertical
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn

class Prompts(ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, Vertical):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("ctrl+t", "duplicate", "Duplicate"),
        ("escape", "cancel", "Cancel")
    ]

    def __init__(self) -> None:
        super().__init__()
        self.settings = self.app.settings
        self.id = "manage-prompts"
        self.classes = "manage"
        self.new_prompt = False

    def duplicate(self) -> None:
        self.new_prompt = True
        self.uuid = str(uuid4())
        self.query_one("#name").value = self.uuid

    def new(self) -> None:
        self.new_prompt = True
        self.uuid = str(uuid4())
        self.prompt = {
                "name": self.uuid,
                "text": "You are a helpful AI assistant."
        }

    def load(self, uuid: str) -> None:
        self.new_prompt = False
        self.uuid = uuid
        self.prompt = deepcopy(self.settings.prompts[uuid])

    def store_values(self) -> None:
        name = self.query_one("#name").value
        text = self.query_one("#text").text
        self.prompt = {
                "name": name,
                "text": text
        }

    def save(self) -> None:
        self.settings.prompts[self.uuid] = deepcopy(self.prompt)
        self.settings.save_prompts()

    def delete(self) -> None:
        del self.settings.prompts[self.uuid]
        self.settings.save_prompts()
