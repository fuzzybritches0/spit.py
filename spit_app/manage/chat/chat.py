import os
import shutil
from time import time
from datetime import datetime
from copy import deepcopy
from .actions import ActionsMixIn
from spit_app.manage.manage import Manage

class Chat(ActionsMixIn, Manage):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("ctrl+i", "archive", "Archive"),
        ("ctrl+i", "unarchive", "Un-archive"),
        ("escape", "cancel", "Cancel")
    ]
    BUTTONS = (
        ("save", "Save"),
        ("delete", "Delete"),
        ("archive", "Archive"),
        ("unarchive", "Un-archive"),
        ("cancel", "Cancel")
    )
    NEW = {
        "desc": { "stype": "string", "empty": False, "desc": "Description", "value": "New Chat" },
        "endpoint": { "stype": "select_no_default", "desc": "Endpoint", "ameth": "endpoint_list" },
        "prompt": { "stype": "select", "desc": "System Prompt", "ameth": "prompt_list" }
    }

    def __init__(self, new_chat: bool = False) -> None:
        super().__init__()
        if new_chat:
            self.id = "new-chat"
            self.new()
            self.mount_screen = self.edit_manage_screen
        else:
            self.id = "manage-chat"
        self.classes = "manage"
        self.managed = None
        self.settings = self.app.settings
        self.path = self.app.settings.path
        self.new_manage = new_chat
        self.cur_dir = "chats"

    def is_loaded(self) -> bool:
        try:
            self.app.query_one("#main").query_one(f"#chat-{self.uuid}")
            return True
        except:
            return False

    def unarchive(self) -> bool:
        file = f"chat-{self.uuid}.json"
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
        file = f"chat-{self.uuid}.json"
        file_chat = self.path["chats"] / file
        file_archive = self.path["chats_archive"] / file
        try:
            shutil.copy(file_chat, file_archive)
        except Exception as exception:
            self.app.exception = exception
            return False
        return self.delete()

    def delete(self) -> bool:
        file_name = f"chat-{self.uuid}.json"
        if self.is_loaded():
            self.app.query_one("#main").query_one(f"#chat-{self.uuid}").remove()
        try:
            os.remove(self.path[self.cur_dir] / file_name)
        except Exception as exception:
            self.app.exception = exception
            return False
        if not self.cur_dir == "chats_archive":
            self.app.query_one("#side-panel").remove_option(f"chat-{self.uuid}")
            if self.app.query_one("#side-panel").highlighted:
                self.app.query_one("#side-panel").highlighted-=1
        return True

    def load(self, uuid: str) -> None:
        self.new_manage = False
        self.uuid = uuid
        self.manage = deepcopy(self.NEW)
        content = self.app.read_json(f"{self.cur_dir}/chat-{self.uuid}.json")
        self.manage = content["settings"]

    def save_managed(self) -> None:
        if self.new_manage:
            content = {}
            content["ctime"] = time()
            content["settings"] = self.manage
            content["messages"] = []
            self.app.write_json(f"{self.cur_dir}/chat-{self.uuid}.json", content)
        else:
            if self.is_loaded():
                chat = self.app.query_one("#main").query_one(f"#chat-{self.uuid}")
                chat.chat_desc = self.manage["desc"]["value"]
                chat.chat_endpoint = self.manage["endpoint"]["value"]
                chat.chat_prompt = self.manage["prompt"]["value"]
                ctime = chat.chat_ctime
                desc = chat.chat_desc
                chat.write_chat_history()
            else:
                content = self.app.read_json(f"{self.cur_dir}/chat-{self.uuid}.json")
                content["settings"] = self.manage
                ctime = content["ctime"]
                desc = content["settings"]["desc"]["value"]
                self.app.write_json(f"{self.cur_dir}/chat-{self.uuid}.json", content)
            ctime = datetime.fromtimestamp(int(ctime))
            self.app.query_one("#side-panel").replace_option_prompt(f"chat-{self.uuid}", f"\n{desc}\n{ctime}\n")

    def get_managed(self) -> dict:
        chats = os.listdir(self.path[self.cur_dir])
        chats = sorted(chats, reverse=True)
        chat_dict = {}
        for chat in chats:
            content = self.app.read_json(f"{self.cur_dir}/{chat}")
            id = chat[5:-5]
            desc = content["settings"]["desc"]["value"]
            local_ctime = datetime.fromtimestamp(int(content["ctime"]))
            chat_dict[id] = {"name": {"value": f"{desc}\n{local_ctime}"}}
        return chat_dict

    def endpoint_list(self, default: bool = False) -> list:
        tup = ()
        for key in self.settings.endpoints.keys():
            tup += ((self.settings.endpoints[key]["name"]["value"], key),)
        return tup

    def prompt_list(self, default: bool = False) -> list:
        tup = ()
        for key in self.settings.prompts.keys():
            tup += ((self.settings.prompts[key]["name"]["value"], key),)
        return tup
