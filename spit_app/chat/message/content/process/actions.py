import json
from textual.widgets import Select
from .text_area_edit import TextAreaEdit
from .text_area_tool import TextAreaTool
from spit_app.chat.textual_message import RemoveProcess

bindings = [
    ("c", "copy", "Copy"),
    ("e", "edit", "Edit"),
    ("x", "remove", "Rem."),
    ("ctrl+enter", "save", "Save"),
    ("ctrl+escape", "cancel", "Cancel")
]

class ActionsMixIn:
    def action_copy(self) -> None:
        if type(self.message.message[self.scontent]) is str:
            self.app.copy_to_clipboard(self.message.message[self.scontent])
        else:
            _type = self.message.message[self.scontent][self.count]["type"]
            if _type == "function":
                self.app.copy_to_clipboard(json.dumps(self.message.message[self.scontent][self.count][_type]))
            else:
                self.app.copy_to_clipboard(self.message.message[self.scontent][self.count][_type])

    async def action_save(self) -> None:
        await self.edit.save()

    async def action_cancel(self) -> None:
        await self.edit.cancel()

    async def action_remove(self) -> None:
        if not self.message.is_removing and not self.is_removing:
            self.is_removing = True
            if type(self.message.message[self.scontent]) is str:
                self.message.post_message(RemoveProcess(self.scontent))
            else:
                self.message.post_message(RemoveProcess(self.scontent, self.count))

    async def action_edit(self) -> None:
        self.message.is_edit += 1
        self.is_edit = True
        if self.scontent == "tool_calls":
            async with self.batch():
                await self.remove_children()
                self.edit = TextAreaTool(self)
                await self.edit.mount()
        else:
            async with self.batch():
                await self.remove_children()
                self.edit = TextAreaEdit(self)
                await self.mount(self.edit)

    async def on_select_changed(self, event: Select.Changed) -> None:
        for child in self.children[2:]:
            await child.remove()
        self.edit.tool_change = event.control.value
        await self.edit.mount(False, False)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.chat.is_working() or self.message.is_removing or self.is_removing:
            return False
        if action == "copy":
            if self.is_edit:
                return False
            if type(self.message.message[self.scontent]) is str and not self.message.message[self.scontent]:
                return False
            if type(self.message.message[self.scontent]) is dict:
                _type = self.message.message[self.scontent][self.count]["type"]
                if not self.message.message[self.scontent][self.count][_type]:
                    return False
        if action == "edit" or action == "remove":
            if self.is_edit or not self.chat_view.is_edit:
                return False
        if action == "save" or action == "cancel":
            if not self.is_edit or not self.chat_view.is_edit:
                return False
        return True
