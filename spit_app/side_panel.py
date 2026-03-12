# SPDX-License-Identifier: GPL-2.0
import os
from datetime import datetime
from spit_app.chat.chat import Chat
from spit_app.manage.chat.chat import Chat as ManageChats
from spit_app.manage.endpoint.endpoint import Endpoints as ManageEndpoints
from spit_app.manage.model_settings.model_settings import ModelSettings as ManageModelSettings
from spit_app.manage.prompt.prompt import Prompts as ManagePrompts
from spit_app.manage.tool_settings.tool_settings import ToolSettings as ManageToolSettings
from spit_app.modal_screens import InfoScreen 
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

    def option_list(self) -> None:
        Options = []
        Options.append(Option("\nCreate New Chat\n", id="new-chat"))
        Options.append(None)
        chats = os.listdir(self.path["chats"])
        chats = sorted(chats, reverse=True)
        for chat in chats:
            content = self.app.read_json(f"chats/{chat}")
            id = chat[:-5]
            desc = content["settings"]["desc"]["value"]
            ctime = datetime.fromtimestamp(int(content["ctime"]))
            Options.append(Option(f"\n{desc}\n{ctime}\n", id=id))
        Options.append(None)
        Options.append(Option("\nManage Chats\n", id="manage-chat"))
        Options.append(Option("\nManage Endpoints\n", id="manage-endpoint"))
        Options.append(Option("\nManage Model Settings\n", id="manage-model-settings"))
        Options.append(Option("\nManage System Prompts\n", id="manage-prompt"))
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
        for cont in self.app.query_one("#main").children:
            cont.display = False
            if cont.id == id:
                cont.display = True
                cont.focus()
                self.app.focused_container = cont
                if cont.id.startswith("chat-"):
                    cont.query_one("#chat-settings").update_selects()
                ret = True
        if ret:
            return None
        if id.startswith("chat"):
            await self.app.query_one("#main").mount(Chat(id))
        elif id == "new-chat":
            if self.settings.endpoints:
                await self.app.query_one("#main").mount(ManageChats(True))
            else:
                await self.app.push_screen(InfoScreen("No endpoints set! Please set up an endpoint first"))
        elif id == "manage-chat":
            await self.app.query_one("#main").mount(ManageChats())
        elif id == "manage-endpoint":
            await self.app.query_one("#main").mount(ManageEndpoints())
        elif id == "manage-model-settings":
            await self.app.query_one("#main").mount(ManageModelSettings())
        elif id == "manage-prompt":
            await self.app.query_one("#main").mount(ManagePrompts())
        elif id == "manage-tool-settings":
            await self.app.query_one("#main").mount(ManageToolSettings())

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "quit":
            self.app.action_exit_app()
        await self.option_selected(event.option.id)

    def on_mount(self) -> None:
        self.option_list()
