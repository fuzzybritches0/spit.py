import json
from textual.widgets import Select
from .text_area_edit import TextAreaEdit
from .text_area_tool import TextAreaTool

bindings = [
    ("e", "edit", "Edit"),
    ("x", "remove", "Remove"),
    ("ctrl+enter", "save", "Save"),
    ("ctrl+escape", "cancel", "Cancel")
]

class ActionsMixIn:
    async def action_save(self) -> None:
        await self.edit.save()

    async def action_cancel(self) -> None:
        await self.edit.cancel()

    async def action_remove(self) -> None:
        index = self.chat_view.messages.index(self.message.message)
        self.chat.undo.append_undo("change", self.message.message, index)
        if type(self.message.message[self.scontent]) is str:
            del self.message.message[self.scontent]
        else:
            del self.message.message[self.scontent][self.count]
        await self.message.reset()
        await self.message.finish()
        self.chat.write_chat_history()

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
        if self.chat.is_working() or not self.chat_view.is_edit:
            return False
        if action == "edit" or action == "remove":
            if self.is_edit:
                return False
        if action == "save" or action == "cancel":
            if not self.is_edit:
                return False
        return True
