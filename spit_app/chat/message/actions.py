import json
import random
import hashlib
from .content.process.process import Process
from .content.process.text_area_tool import TextAreaTool
from spit_app.chat.textual_message import RemoveMessage, RemoveProcess

bindings = [
    ("s", "show_cot", "Show CoT"),
    ("s", "hide_cot", "Hide CoT"),
    ("x", "remove", "Remove"),
    ("t", "add_tool", "Add Tool")
]

class ActionsMixIn:
    def action_show_cot(self) -> None:
        self.pr["reasoning"].display = True
        self.app.refresh_bindings()

    def action_hide_cot(self) -> None:
        if self.children[1].children[0].has_focus:
            self.focus(scroll_visible=False)
        self.pr["reasoning"].display = False
        self.app.refresh_bindings()

    def action_remove(self) -> None:
        if not self.is_removing:
            self.is_removing = True
            self.chat_view.post_message(RemoveMessage(self.chat_view.children.index(self)))

    async def action_add_tool(self) -> None:
        hash_id = random.randint(1, 1000000000000)
        hash_id = hashlib.md5(str(hash_id).encode())
        hash_id = hash_id.hexdigest()
        name = self.chat.cs("tools")[0]
        function = {"id": hash_id, "type": "function", "function": {"name": name, "arguments": "{}"}}
        if not "tool_calls" in self.pr:
            self.message["tool_calls"] = [function]
            await self.maybe_mount_process("tool_calls")
        else:
            self.message["tool_calls"].append(function)
        index = len(self.message["tool_calls"])-1
        await self.pr["tool_calls"].mount(Process(self.chat, self, "tool_calls", index))
        process = self.pr["tool_calls"].children[-1]
        process.edit = TextAreaTool(process, True)
        self.is_edit += 1
        process.is_edit = True
        await process.edit.mount()
        process.focus()

    def has_reasoning(self) -> bool:
        if self.message["role"] == "assistant" and self.message["reasoning"]:
            return True
        return False

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "show_cot":
            if self.chat_view.is_edit:
                return False
            if not "reasoning" in self.pr:
                return False
            if self.pr["reasoning"].display:
                return False
        elif action == "hide_cot":
            if self.chat_view.is_edit:
                return False
            if not "reasoning" in self.pr:
                return False
            if not self.pr["reasoning"].display:
                return False
        elif action == "remove":
            if self.chat.is_working() or self.is_edit or not self.chat_view.is_edit:
                return False
        elif action == "add_tool":
            if not self.role == "assistant" or not self.chat_view.is_edit:
                return False
        return True

    async def on_remove_process(self, message: RemoveProcess) -> None:
        if message.index:
            await self.pr[message.scontent].children[message.index].remove()
            del self.message[message.scontent][message.index]
            if self.message[message.scontent]:
                return None
        await self.pr[message.scontent].remove()
        del self.message[message.scontent]
