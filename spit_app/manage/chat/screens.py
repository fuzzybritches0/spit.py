import os
import json
from datetime import datetime
from textual.containers import Horizontal
from textual.widgets import Label, Select, Input, Button, OptionList
from textual.widgets.option_list import Option
from textual.validation import Function
from typing import Generator, List

class ScreensMixIn:
    async def select_main_screen(self) -> None:
        Options = [Option("\nCreate new Chat\n", id="select-new-chat")]
        for chat in os.listdir(self.app.settings.data_path):
            if chat.startswith("chat-") and chat.endswith(".json"):
                with open(self.app.settings.data_path / chat, "r") as file:
                    content = json.load(file)
                id = chat[:-5]
                desc = content["desc"]
                local_ctime = datetime.fromtimestamp(int(content["ctime"]))
                Options.append(Option(f"{desc}\n{local_ctime}\n", id=id))
        await self.mount(OptionList(*Options, id="option-list"))
        self.children[0].focus()

    def endpoint_list(self) -> Generator[str, str]:
        for key in self.settings.endpoints.keys():
            name = self.settings.endpoints[key]["values"]["name"]
            yield name, key

    def prompt_list(self) -> Generator[str, str]:
        for key in self.settings.prompts.keys():
            name = self.settings.prompts[key]["name"]
            yield name, key

    async def edit_chat(self, chat: str|None = None) -> None:
        content = None
        self.cur_chat = None
        if chat:
            self.cur_chat = chat
            chat += ".json"
            with open(self.app.settings.data_path / chat, "r") as file:
                content = json.load(file)
        Validators = [Function(self.val.is_not_empty)]
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
            await self.mount(Input(id="desc", validators=Validators))
            await self.mount(Label("Endpoint:"))
            await self.mount(Select(((name, key) for name, key in self.endpoint_list()),
                                id="endpoint", allow_blank=False))
            await self.mount(Label("System Prompt:"))
            await self.mount(Select(((name, key) for name, key in self.prompt_list()),
                                id="prompt", prompt="None"))
        await self.mount(Horizontal(
            Button("Save", id="save"),
            Button("Delete", id="delete"),
            Button("Cancel", id="cancel"),
            id="save-delete-cancel"
        ))
        self.children[1].focus()
