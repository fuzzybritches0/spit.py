# SPDX-License-Identifier: GPL-2.0
import asyncio
from textual import events, work
from textual.containers import Horizontal
from textual.widgets import Label, Select
from spit_app.endpoints.llamacpp import get_models, get_model_capabilities, get_models_tuple

class ChatSettings(Horizontal):
    BINDINGS = [("ctrl+s", "leave_settings", "Leave settings")]

    def __init__(self, chat) -> None:
        super().__init__()
        self.id = "chat-settings"
        self.chat = chat
        self.cs = chat.cs
        self.settings = chat.settings
        self.selects = [ 1, 3, 5]
        self.models = []

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.value == "none":
            return None
        if event.control.id == "select-endpoint":
            self.cs("endpoint", event.value)
            self.update_models()
        if event.control.id == "select-model":
            self.cs("model", event.value)
            self.chat.model_capabilities = get_model_capabilities(self.models, self.cs("model"))
        if event.control.id == "select-model-settings":
            if event.value == Select.NULL:
                self.cs("model_settings", None)
            else:
                self.cs("model_settings", event.value)
        self.chat.write_chat_history()

    def focus(self) -> None:
        self.children[self.selects[0]].focus()

    def allowed_focus(self) -> None:
        for select in self.selects:
            self.children[select].can_focus = True

    def disallowed_focus(self) -> None:
        for select in self.selects:
            self.children[select].can_focus = False

    def set_value(self, options: tuple, option: str, allow_blank: bool) -> str:
        if not option or not option in (i for n, i in options):
            if allow_blank:
                return Select.NULL
            else:
                return options[0][1]
        return option

    def action_leave_settings(self) -> None:
        self.chat.focus()

    async def on_mount(self) -> None:
        options = (("None", "none"),)
        await self.mount(Label("Endpoint:"))
        await self.mount(Select(options, id="select-endpoint", allow_blank=False, compact=True))
        await self.mount(Label("Model:"))
        await self.mount(Select(options, id="select-model", allow_blank=False, compact=True))
        await self.mount(Label("Settings:"))
        await self.mount(Select(options, id="select-model-settings", allow_blank=True, compact=True))
        self.update_selects()
        self.disallowed_focus()

    @work(exclusive=True, exit_on_error=False)
    async def update_models(self) -> None:
        self.children[3].set_options((("None", "none"),))
        count = 0
        while True:
            capabilities = self.chat.model_capabilities
            if not self.cs("endpoint") in self.app.endpoint_list():
                return None
            endpoint = self.app.get_endpoint(self.cs("endpoint"))
            self.models = await get_models(endpoint)
            if self.models:
                options = get_models_tuple(self.models)
                self.children[3].set_options(options)
                self.children[3].value = self.set_value(options, self.cs("model"), False)
                self.cs("model", self.children[3].selection)
                self.chat.model_capabilities = get_model_capabilities(self.models, self.cs("model"))
                if not capabilities == self.chat.model_capabilities:
                    self.chat.refresh_bindings()
                return None
            else:
                if not self.cs("model") == self.children[3].selection:
                    self.cs("model", self.children[3].selection)
                    self.chat.refresh_bindings
                count += 1
                if count > 60:
                    return None
                await asyncio.sleep(10)

    def update_selects(self) -> None:
        options = self.get_options()
        self.children[1].set_options(options[0])
        self.children[5].set_options(options[1])
        self.set_selects(options)
        self.update_models()

    def get_options(self) -> list:
        options = []
        options.append(self.app.endpoint_list_tuple())
        options.append(self.model_settings_options())
        return options

    def set_selects(self, options: list) -> None:
        self.children[1].value = self.set_value(options[0], self.cs("endpoint"), False)
        self.cs("endpoint", self.children[1].selection)
        self.children[5].value = self.set_value(options[1], self.cs("model_settings"), True)
        self.cs("model_settings", self.children[5].selection)
        self.chat.write_chat_history()

    async def on_descendant_focus(self) -> None:
        self.allowed_focus()

    def on_descendant_blur(self) -> None:
        if not self.has_focus_within:
            self.disallowed_focus()

    def model_settings_options(self) -> None:
        tup = ()
        for key in self.settings.models.keys():
            tup += ((self.settings.models[key]["name"]["value"], key),)
        return tup
