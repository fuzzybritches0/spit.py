# SPDX-License-Identifier: GPL-2.0
import os
import json
from datetime import datetime
from spit_app.chat.chat import Chat
from spit_app.manage.chat.chat import Chat as ManageChats
from spit_app.manage.endpoint.endpoint import Endpoints as ManageEndpoints 
from spit_app.manage.prompt.prompt import Prompts as ManagePrompts
from spit_app.manage.tool_settings.tool_settings import ToolSettings as ManageToolSettings
from textual.widgets import OptionList
from textual.widgets.option_list import Option

class SidePanel(OptionList):
    def __init__(self) -> None:
        super().__init__()
        self.id = "side-panel"
        self.settings = self.app.settings
        self.path = self.settings.path

    def update_option_prompt(self, chat_id: str) -> None:
        chat = self.app.query_one("#main").query_one(f"#{chat_id}")
        ctime = chat.chat_ctime
        desc = chat.chat_desc
        ctime = datetime.fromtimestamp(int(ctime))
        self.replace_option_prompt(chat_id, f"\n{desc}\n{ctime}\n")

    async def add_option_chat(self, chat_id) -> None:
        chat = self.app.query_one("#main").query_one(f"#{chat_id}")
        await self.option_selected(chat_id)
        options = self.options
        ctime = datetime.fromtimestamp(int(chat.chat_ctime))
        option = Option(f"{chat.chat_desc}\n{ctime}\n", id=chat_id)
        new_options = options[0:1] + [option]
        if len(options) < 9:
            new_options.append(None)
        new_options += options[1:]
        self.set_options(new_options)
        self.highlighted = 1

    def option_list(self) -> None:
        Options = []
        Options.append(Option("\nCreate New Chat\n", id="new-chat"))
        Options.append(None)
        chats = os.listdir(self.path["chats"])
        chats = sorted(chats, reverse=True)
        for chat in chats:
            with open(self.app.settings.chats / chat, "r") as file:
                content = json.load(file)
            id = chat[:-5]
            desc = content["desc"]
            ctime = datetime.fromtimestamp(int(content["ctime"]))
            Options.append(Option(f"\n{desc}\n{ctime}\n", id=id))
        Options.append(None)
        Options.append(Option("\nManage Chats\n", id="manage-chats"))
        Options.append(Option("\nManage Endpoints\n", id="manage-endpoints"))
        Options.append(Option("\nManage System Prompts\n", id="manage-prompts"))
        Options.append(Option("\nManage Tool Settings\n", id="manage-tool-settings"))
        Options.append(None)
        Options.append(Option("\nHelp\n", id="help"))
        Options.append(Option("\nAbout\n", id="about"))
        Options.append(None)
        Options.append(Option("\nQuit\n", id="quit"))
        self.clear_options()
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
                if cont.id.startswith("chat"):
                    cont.chat_view.focus()
                else:
                    cont.focus()
                ret = True
            index+=1
        if ret:
            return None
        if id.startswith("chat"):
            self.settings.active_chat = id
            self.settings.save()
            await self.app.query_one("#main").mount(Chat(id))
        elif id == "new-chat":
            await self.app.query_one("#main").mount(ManageChats(True))
        elif id == "manage-chats":
            await self.app.query_one("#main").mount(ManageChats())
        elif id == "manage-endpoints":
            await self.app.query_one("#main").mount(ManageEndpoints())
        elif id == "manage-prompts":
            await self.app.query_one("#main").mount(ManagePrompts())
        elif id == "manage-tool-settings":
            await self.app.query_one("#main").mount(ManageToolSettings())

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "quit":
            self.app.action_exit_app()
        await self.option_selected(event.option.id)

    def on_mount(self) -> None:
        self.option_list()
