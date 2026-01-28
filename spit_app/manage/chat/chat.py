import os
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
        self.path = self.settings.path
        if self.new_chat:
            self.id = "new-chat"
        else:
            self.id = "manage-chats"
        self.classes = "manage"
        self.cur_dir = "chats"
        self.cur_chat = None

    def new(self, desc: str, endpoint: str, prompt: str) -> bool:
        self.ctime = time()
        self.uuid = "chat-" + str(self.ctime).replace(".", "-")
        content = {"ctime": self.ctime, "desc": desc, "endpoint": endpoint,
                   "prompt": prompt, "messages": []}
        file = f"{self.cur_dir}/{self.uuid}.json"
        return self.app.write_json(file, content)

    def save(self) -> bool:
        if self.valid_values():
            desc = self.query_one("#desc").value
            endpoint = self.query_one("#endpoint").value
            prompt = self.query_one("#prompt").value
            if prompt == Select.BLANK:
                prompt = None
            if self.cur_chat:
                return self.update(desc, endpoint, prompt)
            else:
                return self.new(desc, endpoint, prompt)

    def is_loaded(self) -> bool:
        try:
            self.app.query_one("#main").query_one(f"#{self.cur_chat}")
            return True
        except:
            return False

    def unarchive(self) -> bool:
        file = self.cur_chat + ".json"
        file_chat = self.path["chats"] / file
        file_archive = self.path["chats_archive"] / file
        try:
            shutil.copy(file_archive, file_chat)
            os.remove(file_archive)
        except Exception as exception:
            self.app.exception = exception
            return False
        self.app.query_one("#side-panel").option_list()
        return True

    def archive(self) -> bool:
        file = self.cur_chat + ".json"
        file_chat = self.path["chats"] / file
        file_archive = self.path["chats_archive"] / file
        try:
            shutil.copy(file_chat, file_archive)
        except Exception as exception:
            self.app.exception = exception
            return False
        return self.delete()

    def delete(self) -> bool:
        file_name = self.cur_chat + ".json"
        if self.is_loaded():
            self.app.query_one("#main").query_one(f"#{self.cur_chat}").remove()
        try:
            os.remove(self.path[self.cur_dir] / file_name)
        except Exception as exception:
            self.app.exception = exception
            return False
        if not self.cur_dir == "chats_archive":
            self.app.query_one("#side-panel").remove_option(self.cur_chat)
            if self.app.query_one("#side-panel").highlighted:
                self.app.query_one("#side-panel").highlighted-=1
        return True

    def update(self, desc: str, endpoint: str, prompt: str) -> bool:
        if self.is_loaded():
            chat = self.app.query_one("#main").query_one(f"#{self.cur_chat}")
            chat.chat_desc = desc
            chat.chat_endpoint = endpoint
            chat.chat_prompt = prompt
            ctime = chat.chat_ctime
            if not chat.write_chat_history():
                return False
        else:
            file_name = self.cur_chat + ".json"
            content = self.app.read_json(f"{self.cur_dir}/{file_name}")
            content["desc"] = desc
            content["endpoint"] = endpoint
            content["prompt"] = prompt
            ctime = content["ctime"]
            if not self.app.write_json(f"{self.cur_dir}/{file_name}", content):
                return False
        ctime = datetime.fromtimestamp(int(ctime))
        self.app.query_one("#side-panel").replace_option_prompt(self.cur_chat, f"\n{desc}\n{ctime}\n")
        return True
