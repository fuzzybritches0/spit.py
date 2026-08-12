from textual.events import Focus
from textual.widgets import Label
from spit_app.manage.endpoint.common import Common
from spit_app.manage.endpoint.actions import ActionsMixIn
from spit_app.manage.endpoint.handlers import HandlersMixIn
from spit_app.manage.endpoint.screens import ScreensMixIn
from spit_app.manage.endpoint.validation import ValidationMixIn
from spit_app.manage.manage import Manage
from spit_app.llamacpp.models import NEW_MODELS_SERVER_SETTINGS, MODELS_SERVER_SETTINGS
from copy import deepcopy

class ServerSettings(Common, ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, Manage):
    NEW = NEW_MODELS_SERVER_SETTINGS
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+i", "remove_setting", "Remove Setting"),
        ("ctrl+o", "add_setting", "Add Setting"),
        ("ctrl+r", "reset", "Reset")
    ]
    BUTTONS = (
        ("save", "Save Settings"),
        ("reset", "Reset")
    )

    def __init__(self, model_id) -> None:
        super().__init__("server-settings")
        self.classes = "auto-height"
        self.uuid = model_id
        self.managed = self.settings.server_settings
        if not self.uuid in self.managed:
            self.manage = deepcopy(self.NEW)
        else:
            self.manage = deepcopy(self.managed[self.uuid])
        self.new_manage = True
        self.old_manage = deepcopy(self.manage)
        self.save_managed = self.settings.save_server_settings
        self.load_managed = self.settings.load_server_settings

    async def action_reset(self) -> None:
        if not self.manage == MODELS_SERVER_SETTINGS[self.uuid]:
            del self.managed[self.uuid]
            self.save_managed()
            self.load_managed()
            self.managed = self.settings.server_settings
            self.manage = deepcopy(self.managed[self.uuid])
            await self.remove_children()
            await self.edit_manage_screen()
            await self.after_action_save()
        else:
            await self.remove_children()
            await self.edit_manage_screen()
        await self.parent.parent.update_input_devices()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool|None:
        if action == "reset":
            if not self.uuid in MODELS_SERVER_SETTINGS:
                return False
        return True

    async def after_action_save(self) -> None:
        self.app.action_notify(f"Settings saved!")
        await self.app.server.stop()
        self.app.server.start()
        self.old_manage = deepcopy(self.manage)

    async def after_action(self, action: str) -> None:
        if action == "save":
            if not self.manage == self.old_manage:
                await self.after_action_save()

    def on_focus(self, event: Focus) -> None:
        event.prevent_default()
        self.app.query_one("#manage-llamacpp").focus()

    def on_descendant_focus(self) -> None:
        pass
