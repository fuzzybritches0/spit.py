import os
from datetime import datetime
from textual.containers import Horizontal
from textual.widgets import Label, Select, Input, Button, OptionList
from textual.widgets.option_list import Option
from textual.validation import Function
from typing import Generator, List

class ScreensMixIn:
    async def select_main_screen(self) -> None:
        Options = []
        if not self.cur_dir == "chats_archive":
            Options.append(Option("\nCreate new Chat\n", id="select-new-chat"))
        chats = os.listdir(self.path[self.cur_dir])
        chats = sorted(chats, reverse=True)
        for chat in chats:
            content = self.app.read_json(f"{self.cur_dir}/{chat}")
            id = chat[:-5]
            desc = content["desc"]
            local_ctime = datetime.fromtimestamp(int(content["ctime"]))
            Options.append(Option(f"{desc}\n{local_ctime}\n", id=id))
        if self.cur_dir == "chats_archive":
            Options.append(Option("\nLeave archive\n", id="select-leave-archive"))
        else:
            Options.append(Option("\nArchive\n", id="select-archive"))
        await self.mount(OptionList(*Options, id="option-list"))
        self.children[0].focus()

    def endpoint_list(self) -> Generator[str, str]:
        for key in self.settings.endpoints.keys():
            name = self.settings.endpoints[key]["name"]["value"]
            yield name, key

    def prompt_list(self) -> Generator[str, str]:
        for key in self.settings.prompts.keys():
            name = self.settings.prompts[key]["name"]["value"]
            yield name, key

    async def edit_chat(self, chat: str|None = None) -> None:
        content = None
        self.cur_chat = None
        if chat:
            self.cur_chat = chat
            chat += ".json"
            content = self.app.read_json(f"{self.cur_dir}/{chat}")
        Validators = [Function(self.is_not_empty)]
        await self.mount(Label("Description:"))
        if content:
            await self.mount(Input(id="desc", value=content["desc"], validators=Validators))
            await self.mount(Label("Endpoint:"))
            await self.mount(Select(((name, key) for name, key in self.endpoint_list()),
                                value=content["endpoint"], id="endpoint", allow_blank=False))
            await self.mount(Label("System Prompt:"))
            value = content["prompt"]
            if not content["prompt"]:
                value = Select.BLANK
            await self.mount(Select(((name, key) for name, key in self.prompt_list()),
                                value=value, id="prompt", prompt="None"))
        else:
            await self.mount(Input(id="desc", value="New Chat", validators=Validators))
            await self.mount(Label("Endpoint:"))
            await self.mount(Select(((name, key) for name, key in self.endpoint_list()),
                                id="endpoint", allow_blank=False))
            await self.mount(Label("System Prompt:"))
            await self.mount(Select(((name, key) for name, key in self.prompt_list()),
                                id="prompt", prompt="None"))
        if chat:
            if self.cur_dir == "chats_archive":
                await self.mount(Horizontal(
                    Button("Un-archive", id="unarchive"),
                    Button("Delete", id="delete"),
                    Button("Cancel", id="cancel"),
                    id="save-delete-cancel"
                ))
            else:
                await self.mount(Horizontal(
                    Button("Save", id="save"),
                    Button("Delete", id="delete"),
                    Button("Archive", id="archive"),
                    Button("Cancel", id="cancel"),
                    id="save-delete-cancel"
                ))
        else:
            if self.new_chat:
                await self.mount(Horizontal(
                    Button("Save", id="save"),
                    id="save-delete-cancel"
                ))
            else:
                await self.mount(Horizontal(
                    Button("Save", id="save"),
                    Button("Cancel", id="cancel"),
                    id="save-delete-cancel"
                ))
        self.children[1].focus()
