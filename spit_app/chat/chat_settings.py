# SPDX-License-Identifier: GPL-2.0
from textual import events
from textual.containers import Horizontal
from textual.widgets import Label, Select
from spit_app.endpoints.llamacpp import get_models_tuple

class ChatSettings(Horizontal):
    BINDINGS = [("ctrl+s", "leave_settings", "Leave settings")]

    def __init__(self, chat) -> None:
        super().__init__()
        self.id = "chat-settings"
        self.chat = chat
        self.settings = chat.settings
        self.selects = [ 1, 3, 5]
        self.selects_updating = False

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.value == "none" or self.selects_updating:
            return None
        if event.control.id == "select-endpoint":
            self.chat.chat_endpoint = event.value
            self.query_one("#select-model").set_options(await self.model_options())
        if event.control.id == "select-model":
            self.chat.chat_model = event.value
        if event.control.id == "select-model-settings":
            self.chat.chat_model_settings = event.value
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
                return Select.BLANK
            else:
                return options[0][1]
        return option

    def action_leave_settings(self) -> None:
        self.chat.focus()

    async def on_mount(self) -> None:
        await self.update_selects()
        self.disallowed_focus()

    async def update_selects(self) -> None:
        self.selects_updating = True
        await self.remove_children()
        options = self.endpoint_options()
        await self.mount(Label("Endpoint:"))
        await self.mount(Select(options, id="select-endpoint", allow_blank=False, compact=True))
        self.children[-1].set_options(options)
        self.children[-1].value = self.set_value(options, self.chat.chat_endpoint, False)
        self.chat.chat_endpoint = self.children[1].value
        options = await self.model_options()
        await self.mount(Label("Model:"))
        await self.mount(Select(options, id="select-model", allow_blank=False, compact=True))
        self.children[-1].set_options(options)
        self.children[-1].value = self.set_value(options, self.chat.chat_model, False)
        self.chat.chat_model = self.children[3].value
        options = self.model_settings_options()
        await self.mount(Label("Settings:"))
        await self.mount(Select(options, id="select-model-settings", allow_blank=True, compact=True))
        self.children[-1].set_options(options)
        self.children[-1].value = self.set_value(options, self.chat.chat_model_settings, True)
        if self.children[-1].value is Select.BLANK:
            self.chat.chat_model_settings = None
        else:
            self.chat.chat_model_settings = self.children[5].value
        self.chat.write_chat_history()
        self.selects_updating = False

    async def on_descendant_focus(self) -> None:
        self.allowed_focus()
        options = await self.model_options()
        self.children[3].set_options(options)
        self.children[3].value = self.set_value(options, self.chat.chat_model, False)
        self.chat.chat_model = self.children[3].value

    def on_descendant_blur(self) -> None:
        if not self.has_focus_within:
            self.disallowed_focus()

    def endpoint_options(self) -> None:
        tup = ()
        for key in self.settings.endpoints.keys():
            tup += ((self.settings.endpoints[key]["name"]["value"], key),)
        return tup

    async def model_options(self) -> None:
        endpoint = self.settings.endpoints[self.chat.chat_endpoint]
        return await get_models_tuple(endpoint)

    def model_settings_options(self) -> None:
        tup = ()
        for key in self.settings.models.keys():
            tup += ((self.settings.models[key]["name"]["value"], key),)
        return tup
