import os
import json
import shutil
from datetime import datetime
from time import time
from textual.containers import VerticalScroll
from textual.widgets.option_list import Option
from textual.widgets import Select
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn

class Chat(VerticalScroll, ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("ctrl+i", "archive", "Archive"),
        ("ctrl+i", "unarchive", "Un-archive"),
        ("escape", "cancel", "Cancel")
    ]

    def __init__(self, new_chat: bool = False) -> None:
        super().__init__()
        self.new_chat = new_chat
        self.settings = self.app.settings
        if self.new_chat:
            self.id = "new-chat"
        else:
            self.id = "manage-chats"
        self.classes = "manage"
        self.cur_chat = None
        self.chats = self.settings.chats
        self.chats_archive = self.settings.chats_archive
        self.cur_dir = self.chats

    def new(self, desc: str, endpoint: str, prompt: str) -> None:
        self.ctime = time()
        self.uuid = "chat-" + str(self.ctime).replace(".", "-")
        file_name = self.uuid + ".json"
        content = {"ctime": self.ctime, "desc": desc, "endpoint": endpoint,
                   "prompt": prompt, "messages": []}
        file = self.cur_dir / file_name
        with open(file, "w") as f:
            json.dump(content, f)

    def save(self) -> None:
        if self.valid_values():
            desc = self.query_one("#desc").value
            endpoint = self.query_one("#endpoint").value
            prompt = self.query_one("#prompt").value
            if prompt == Select.BLANK:
                prompt = None
            if self.cur_chat:
                self.update(desc, endpoint, prompt)
            else:
                self.new(desc, endpoint, prompt)

    def is_loaded(self) -> bool:
        try:
            self.app.query_one("#main").query_one(f"#{self.cur_chat}")
            return True
        except:
            return False

    def unarchive(self) -> None:
        file = self.cur_chat + ".json"
        file_chat = self.chats / file
        file_archive = self.chats_archive / file
        shutil.copy(file_archive, file_chat)
        os.remove(file_archive)
        self.app.query_one("#side-panel").option_list() 

    def archive(self) -> None:
        file = self.cur_chat + ".json"
        file_chat = self.chats / file
        file_archive = self.chats_archive / file
        shutil.copy(file_chat, file_archive)
        self.delete()

    def delete(self) -> None:
        file_name = self.cur_chat + ".json"
        if self.is_loaded():
            self.app.query_one("#main").query_one(f"#{self.cur_chat}").remove()
        os.remove(self.cur_dir / file_name)
        if not self.cur_dir is self.chats_archive:
            self.app.query_one("#side-panel").remove_option(self.cur_chat)
            if self.app.query_one("#side-panel").highlighted:
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
            with open(self.cur_dir / file_name, "r") as file:
                content = json.load(file)
            content["desc"] = desc
            content["endpoint"] = endpoint
            content["prompt"] = prompt
            ctime = content["ctime"]
            with open(self.cur_dir / file_name, "w") as file:
                json.dump(content, file)
        ctime = datetime.fromtimestamp(int(ctime))
        self.app.query_one("#side-panel").replace_option_prompt(self.cur_chat, f"\n{desc}\n{ctime}\n")
