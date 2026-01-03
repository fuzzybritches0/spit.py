# SPDX-License-Identifier: GPL-2.0
import os
import json
from datetime import datetime
from spit_app.chat.chat import Chat
from spit_app.manage.endpoint.endpoint import Endpoints as ManageEndpoints 
from spit_app.manage.prompt.prompt import Prompts as ManagePrompts
from spit_app.manage.chat.chat import Chat as ManageChats
from textual.widgets import OptionList
from textual.widgets.option_list import Option

class SidePanel(OptionList):
    def __init__(self) -> None:
        super().__init__()
        self.id = "side-panel"
        self.settings = self.app.settings

    def option_list(self) -> None:
        Options = []
        Options.append(Option("\nCreate New Chat\n", id="new-chat"))
        Options.append(None)
        chats = os.listdir(self.app.settings.data_path)
        chats = sorted(chats, reverse=True)
        for chat in chats:
            if chat.startswith("chat-") and chat.endswith(".json"):
                with open(self.app.settings.data_path / chat, "r") as file:
                    content = json.load(file)
                id = chat[:-5]
                desc = content["desc"]
                ctime = datetime.fromtimestamp(int(content["ctime"]))
                Options.append(Option(f"\n{desc}\n{ctime}\n", id=id))
        Options.append(None)
        Options.append(Option("\nManage Chats\n", id="manage-chats"))
        Options.append(Option("\nManage Endpoints\n", id="manage-endpoints"))
        Options.append(Option("\nManage System Prompts\n", id="manage-prompts"))
        Options.append(None)
        Options.append(Option("\nHelp\n", id="help"))
        Options.append(Option("\nAbout\n", id="about"))
        Options.append(None)
        Options.append(Option("\nQuit\n", id="quit"))
        self.add_options(Options)

    async def option_selected(self, id: str) -> None:
        ret = False
        index = 0
        for cont in self.app.query_one("#main").children:
            cont.display = False
            cont.disable = True
            if cont.id == id:
                if cont.id.startswith("chat"):
                    self.settings.active_chat = cont.id
                    self.settings.save()
                cont.display = True
                cont.disable = False
                self.app.focus_first(index)
                ret = True
            index+=1
        if ret:
            return None
        if id.startswith("chat"):
            self.settings.active_chat = id
            self.settings.save()
            await self.app.query_one("#main").mount(Chat(id))
        elif id == "manage-endpoints":
            await self.app.query_one("#main").mount(ManageEndpoints())
        elif id == "manage-prompts":
            await self.app.query_one("#main").mount(ManagePrompts())
        elif id == "manage-chats":
            await self.app.query_one("#main").mount(ManageChats())
        elif id == "new-chat":
            await self.app.query_one("#main").mount(ManageChats(True))

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "quit":
            self.app.action_exit_app()
        await self.option_selected(event.option.id)

    def on_mount(self) -> None:
        self.option_list()
