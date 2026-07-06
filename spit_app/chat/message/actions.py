import json
import random
import hashlib
from .content.process.process import Process
from .content.process.text_area_tool import TextAreaTool
from .content.process.text_area_edit import TextAreaEdit
from spit_app.chat.textual_message import RemoveMessage, RemoveProcess

bindings = [
    ("c", "add_content", "+Cont."),
    ("t", "add_tool", "+Tool"),
    ("a", "add_message_next", "+Msg.↓"),
    ("ctrl+a", "add_message_prev", "+Msg.↑"),
    ("x", "remove", "-"),
    ("s", "show_cot", "CoT"),
    ("s", "hide_cot", "no CoT")
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
            self.chat_view.is_removing = True
            self.chat_view.post_message(RemoveMessage(self.chat.message_index(self.message)))

    async def action_add_content(self) -> None:
        content = {"type": "text", "text": ""}
        if not "content" in self.pr:
            self.message["content"] = [content]
            await self.maybe_mount_process("content")
        else:
            self.message["content"].append(content)
        index = len(self.message["content"])-1
        await self.pr["content"].mount(Process(self.chat, self, "content", index))
        process = self.pr["content"].children[-1]
        process.edit = TextAreaEdit(process, True)
        self.is_edit += 1
        process.is_edit = True
        await process.mount(process.edit)

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

    async def add_message_next(self, index: int, role: str, id: str|None = None, name: str|None = None ) -> None:
        if not id and not name:
            message = {"role": role, "content": []}
        else:
            message = {"role": role, "tool_call_id": id, "name": name, "content": []}
        if len(self.messages) == index:
            self.messages.append(message)
        else:
            self.messages.insert(index, message)
        self.chat.undo.append_undo("insert", self.messages[index], index)
        await self.chat_view.mount_message(index)
        await self.chat_view.children[index].status.update("")
        self.chat.write_chat_history()
        self.chat_view.children[index].focus()

    async def action_add_message_next(self) -> None:
        index = self.chat.message_index(self.message) + 1
        if self.role == "assistant" and "tool_calls" in self.message and self.message["tool_calls"]:
            for tool_call in self.message["tool_calls"]:
                await self.add_message_next(index, "tool", tool_call["id"], tool_call["function"]["name"])
                index += 1
        elif self.role == "assistant":
            await self.add_message_next(index, "user")
        elif self.role == "user":
            await self.add_message_next(index, "assistant")
        elif self.role == "tool":
            await self.add_message_next(index, "assistant")

    async def action_add_message_prev(self) -> None:
        if self.role == "tool":
            tools = []
            for message in self.messages:
                if message["role"] == "tool":
                    tools.append(message)
                else:
                    break
            message = {"role": "assistant", "content": [], "reasoning": "", "tool_calls": []}
            for tool in reversed(tools):
                message["tool_calls"].append({"id": tool["tool_call_id"], "type": "function",
                    "function": {"name": tool["name"], "arguments": "{}"}})
        elif self.role == "assistant":
            message = {"role": "user", "content": []}
        elif self.role == "user":
            message = {"role": "assistant", "content": []}
        self.messages.insert(0, message)
        self.chat.undo.append_undo("insert", self.messages[0], 0)
        await self.chat_view.mount_message(0)
        await self.chat_view.children[0].status.update("")
        if self.role == "tool":
            await self.chat_view.children[0].finish()
        self.chat.write_chat_history()
        self.chat_view.children[0].focus()

    def has_reasoning(self) -> bool:
        if self.message["role"] == "assistant" and self.message["reasoning"]:
            return True
        return False

    def maybe_add_message_next(self) -> None:
        index = self.chat.message_index(self.message)
        if len(self.messages)-1 == index:
            return True
        next_child = self.chat_view.children[index+1]
        if self.role == "assistant" and "tool_calls" in self.message and self.message["tool_calls"]:
            if not next_child.role == "tool":
                return True
        elif self.role == "assistant":
            if not next_child.role == "user":
                return True
        elif self.role == "tool" and not next_child.role == "assistant":
            return True
        elif self.role == "user" and not next_child.role == "assistant":
            return True
        return False

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.is_removing or self.chat_view.is_removing:
            return False
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
        elif action == "add_content":
            if not self.chat_view.is_edit:
                return False
        elif action == "add_tool":
            if not self.role == "assistant" or not self.chat_view.is_edit:
                return False
        elif action == "add_message_next":
            if not self.chat_view.is_edit:
                return False
            return self.maybe_add_message_next()
        elif action == "add_message_prev":
            if not self.chat_view.is_edit:
                return False
            if not self.chat.message_index(self.message) == 0:
                return False
        return True

    async def on_remove_process(self, message: RemoveProcess) -> None:
        index = self.chat.message_index(self.message)
        self.chat.undo.append_undo("change", self.message, index)
        if message.index:
            await self.pr[message.scontent].children[message.index].remove()
            del self.message[message.scontent][message.index]
            if self.message[message.scontent]:
                self.chat.write_chat_history()
                return None
        await self.pr[message.scontent].remove()
        del self.pr[message.scontent]
        del self.message[message.scontent]
        self.chat.write_chat_history()
