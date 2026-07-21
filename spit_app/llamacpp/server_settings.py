from textual.events import Focus
from textual.widgets import Label
from spit_app.manage.endpoint.common import Common
from spit_app.manage.endpoint.actions import ActionsMixIn
from spit_app.manage.endpoint.handlers import HandlersMixIn
from spit_app.manage.endpoint.screens import ScreensMixIn
from spit_app.manage.endpoint.validation import ValidationMixIn
from spit_app.manage.manage import Manage
from copy import deepcopy

class ServerSettings(Common, ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, Manage):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+i", "remove_setting", "Remove Setting"),
        ("ctrl+o", "add_setting", "Add Setting")
    ]
    BUTTONS = (
        ("save", "Save Settings"),
    )
    NEW = {
            "content_length": {"stype": "uinteger", "empty": False,
                "desc": "Content Length (0 = model default)", "value": "0"},
            "jinja": {"stype": "boolean", "desc": "Use Model Chat Template", "value": True},
    }

    def __init__(self, model_id) -> None:
        super().__init__("server-settings")
        self.classes = "auto-height"
        self.uuid = model_id
        if not "server_settings" in self.app.settings.llamacpp:
            self.app.settings.llamacpp["server_settings"] = {}
        if not model_id in self.app.settings.llamacpp["server_settings"]:
            self.app.settings.llamacpp["server_settings"][model_id] = deepcopy(self.NEW)
        self.new_manage = True
        self.manage = self.app.settings.llamacpp["server_settings"][model_id]
        self.managed = self.app.settings.llamacpp["server_settings"]
        self.save_managed = self.app.settings.save

    async def after_action(self, action: str) -> None:
        if action == "save":
            self.app.action_notify(f"Settings saved!")

    def on_focus(self, event: Focus) -> None:
        event.prevent_default()
        self.app.query_one("#manage-llamacpp").focus()

    def on_descendant_focus(self) -> None:
        pass
