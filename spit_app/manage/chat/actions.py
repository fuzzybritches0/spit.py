import os
import json
from datetime import datetime
from uuid import uuid4
from time import time
from textual.widgets import Select
from textual.widgets.option_list import Option
from spit_app.chat.chat import Chat

class ActionsMixIn:
    async def action_delete(self) -> None:
        self.delete()
        await self.remove_children()
        await self.select_main_screen()

    async def action_save(self) -> None:
        if self.valid_values():
            desc = self.query_one("#desc").value
            endpoint = self.query_one("#endpoint").value
            prompt = self.query_one("#prompt").value
            if prompt == Select.BLANK:
                prompt = None
            if self.cur_chat:
                self.update(desc, endpoint, prompt)
            else:
                await self.create_new(desc, endpoint, prompt)
            await self.remove_children()
            await self.select_main_screen()

    async def action_cancel(self) -> None:
        await self.remove_children()
        await self.select_main_screen()

    def is_edit_chat(self) -> bool:
        if self.children and self.children[0].id == "edit-chat":
            return True
        return False

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

    async def create_new(self, desc: str, endpoint: str, prompt: str) -> None:
        ctime = time()
        id = "chat-" + str(uuid4())
        file_name = id + ".json"
        content = {"ctime": ctime, "desc": desc, "endpoint": endpoint,
                   "prompt": prompt, "messages": []}
        file = self.settings.data_path / file_name
        with open(file, "w") as f:
            json.dump(content, f)
        side_panel = self.app.query_one("#side-panel")
        options = side_panel.options
        local_ctime = datetime.fromtimestamp(int(ctime))
        option = Option(f"{desc}\n{local_ctime}\n", id=id)
        new_options = [option] + options
        side_panel.set_options(new_options)
        side_panel.highlighted = 0
        await self.app.query_one("#main").mount(Chat(id))
        await self.app.query_one("#side-panel").option_selected(id)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "cancel" or action == "save" or action == "delete":
            return self.is_edit_chat()
        return True
