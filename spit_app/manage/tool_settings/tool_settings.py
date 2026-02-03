from copy import deepcopy
from spit_app.manage.manage import Manage
from .validation import ValidationMixIn

class ToolSettings(ValidationMixIn, Manage):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "reset", "Reset"),
        ("escape", "cancel", "Cancel")
    ]
    BUTTONS = (
        ("save", "Save"),
        ("reset", "Reset"),
        ("cancel", "Cancel")
    )

    def __init__(self) -> None:
        super().__init__("tool-settings")
        self.managed = self.app.tool_call.tools
        self.save_managed = self.app.settings.save

    def extra_options(self) -> list:
        return []

    def get_name(self, manage: str) -> str:
        return manage

    def load(self, uuid: str) -> None:
        self.uuid = uuid
        self.manage = deepcopy(self.managed[uuid]["settings"])
        for setting in self.manage.keys():
            if uuid in self.app.settings.tool_settings:
                if setting in self.app.settings.tool_settings[uuid]:
                    self.manage[setting]["value"] = self.app.settings.tool_settings[uuid][setting]["value"]

    def store_values(self) -> None:
        super().store_values()
        self.save_settings = {}
        for setting in self.manage.keys():
            if not self.manage[setting]["value"] == self.managed[self.uuid]["settings"][setting]["value"]:
                self.save_settings[setting] = self.manage[setting]

    def reset(self) -> None:
        if self.uuid in self.app.settings.tool_settings:
            del self.app.settings.tool_settings[self.uuid]
            self.save_managed()
            self.load(self.uuid)

    def save(self) -> None:
        if self.save_settings:
            self.app.settings.tool_settings[self.uuid] = deepcopy(self.save_settings)
            self.save_managed()

    async def action_reset(self) -> None:
        self.reset()
        await self.remove_children()
        await self.edit_manage_screen()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.children and self.children[0].id == "option-list":
            return False
        if not action == "cancel" and not action == "save" and not action == "reset" and self.new_manage:
            return False
        return True
