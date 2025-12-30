import os
import json
from datetime import datetime
from time import time
from uuid import uuid4
from textual.containers import Vertical
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn

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

    def new(self, desc: str, endpoint: str, prompt: str) -> None:
        self.ctime = time()
        self.uuid = "chat-" + str(uuid4())
        file_name = self.uuid + ".json"
        content = {"ctime": self.ctime, "desc": desc, "endpoint": endpoint,
                   "prompt": prompt, "messages": []}
        file = self.settings.data_path / file_name
        with open(file, "w") as f:
            json.dump(content, f)

    def is_loaded(self) -> bool:
        try:
            self.app.query_one("#main").query_one(f"#{self.cur_chat}")
            return True
        except:
            return False

    def delete(self) -> None:
        if self.is_loaded():
            self.app.query_one("#main").query_one(f"#{self.cur_chat}").remove()
        file_name = self.cur_chat + ".json"
        os.remove(self.settings.data_path / file_name)
        self.app.query_one("#side-panel").remove_option(self.cur_chat)
        self.app.query_one("#side-panel").highlighted-=1

    def update(self, desc: str, endpoint: str, prompt: str) -> None:
        if self.is_loaded():
            chat = self.app.query_one("#main").query_one(f"#{self.cur_chat}")
            chat.chat_desc = desc
            chat.chat_endpoint = endpoint
            chat.chat_prompt = prompt
            ctime = chat.chat_ctime
            chat.write_chat_history()
        else:
            file_name = self.cur_chat + ".json"
            with open(self.settings.data_path / file_name, "r") as file:
                content = json.load(file)
            content["desc"] = desc
            content["endpoint"] = endpoint
            content["prompt"] = prompt
            ctime = content["ctime"]
            with open(self.settings.data_path / file_name, "w") as file:
                json.dump(content, file)
        ctime = datetime.fromtimestamp(int(ctime))
        self.app.query_one("#side-panel").replace_option_prompt(self.cur_chat, f"\n{desc}\n{ctime}\n")
