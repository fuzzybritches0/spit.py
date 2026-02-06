from copy import deepcopy
from spit_app.manage.manage import Manage

class Prompts(Manage):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("escape", "cancel", "Cancel"),
        ("ctrl+t", "duplicate", "Duplicate")
    ]
    BUTTONS = (
        ("save", "Save"),
        ("cancel", "Cancel"),
        ("delete", "Delete"),
        ("duplicate", "Duplicate")
    )
    NEW = {
            "name": { "stype": "string", "empty": False, "desc": "Name" },
            "text": { "stype": "text", "empty": False, "desc": "System Prompt Text"}
    }

    def __init__(self) -> None:
        super().__init__("prompt")
        self.managed = self.app.settings.prompts
        self.save_managed = self.app.settings.save_prompts

    def valid_setting_name(self, value) -> tuple:
        if value:
            for uuid in self.managed.keys():
                if not self.uuid == uuid and value.strip() == self.managed[uuid]["name"]["value"]:
                    return (False, "Name must be unique!")
        return (True, None)

    async def after_action(self, action: str) -> None:
        if action == "save" or action == "delete":
            await self.app.maybe_remove("manage-chat")
            await self.app.maybe_remove("new-chat")
            await super().after_action(action)
        if not action == "duplicate":
            await super().after_action(action)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.children and self.children[0].id == "option-list":
            return False
        if not action == "cancel" and not action == "save" and self.new_manage:
            return False
        return True
