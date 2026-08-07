from textual.events import Focus
from textual.widgets import Label
from spit_app.manage.endpoint.common import Common
from spit_app.manage.endpoint.actions import ActionsMixIn
from spit_app.manage.endpoint.handlers import HandlersMixIn
from spit_app.manage.endpoint.screens import ScreensMixIn
from spit_app.manage.endpoint.validation import ValidationMixIn
from spit_app.manage.manage import Manage
from spit_app.llamacpp.models import MODELS_SERVER_SETTINGS
from copy import deepcopy

NEW = {
    "device": {"stype": "select_list", "desc": "Use Vulkan devices", "options": [], "value": []},
    "ctx-size": {"stype": "uinteger", "empty": False, "desc": "Prompt Size (0 = default)", "value": 0},
    "jinja": {"stype": "boolean", "desc": "Use Model Chat Template", "value": True},
    "mmproj-offload": {"stype": "boolean", "desc": "Multimodal Projector GPU Offloading", "value": True},
    "swa-full": {"stype": "boolean", "desc": "Use full-size SWA cache", "value": False},
    "cache-prompt": {"stype": "boolean", "desc": "Cache Prompt (default: True)", "value": True},
    "cache-reuse": {"stype": "uinteger", "desc": "Min chunk size to reuse (default: 0)", "value": 256}
}

class ServerSettings(Common, ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, Manage):
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
            self.manage = deepcopy(NEW)
        else:
            self.manage = deepcopy(self.managed[self.uuid])
        self.new_manage = True
        self.old_manage = deepcopy(self.manage)
        self.save_managed = self.settings.save_server_settings
        self.load_managed = self.settings.load_server_settings

    def custom_options(self) -> list:
        options = []
        for setting in self.manage.keys():
            if not setting in NEW:
                options.append((setting, setting))
        return options

    async def action_reset(self) -> None:
        del self.managed[self.uuid]
        self.save_managed()
        self.load_managed()
        self.managed = self.settings.server_settings
        self.manage = deepcopy(self.managed[self.uuid])
        await self.remove_children()
        await self.edit_manage_screen()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool|None:
        if action == "reset":
            if not self.uuid in MODELS_SERVER_SETTINGS:
                return False
        return True

    async def after_action(self, action: str) -> None:
        if action == "save":
            if not self.manage == self.old_manage:
                self.app.action_notify(f"Settings saved!")
                await self.app.server.stop()
                self.app.server.start()
                self.old_manage = deepcopy(self.manage)

    def on_focus(self, event: Focus) -> None:
        event.prevent_default()
        self.app.query_one("#manage-llamacpp").focus()

    def on_descendant_focus(self) -> None:
        pass
