import json
from .content.process.process import Process
from .content.process.text_area_tool import TextAreaTool
from .content.process.text_area_edit import TextAreaEdit
from spit_app.chat.textual_message import RemoveMessage, RemoveProcess, ResetProcess

bindings = [
    ("c", "add_content", "+Cont."),
    ("r", "add_reasoning", "+CoT"),
    ("t", "add_tool", "+Tool"),
    ("a", "add_message_next", "+Msg.↓"),
    ("ctrl+a", "add_message_prev", "+Msg.↑"),
    ("x", "remove", "-Msg."),
    ("s", "show_cot", "CoT"),
    ("s", "hide_cot", "!CoT")
]

class ActionsMixIn:
    def action_show_cot(self) -> None:
        self.cnt["reasoning"].display = True
        self.app.refresh_bindings()

    def action_hide_cot(self) -> None:
        if self.children[1].children[0].has_focus:
            self.focus(scroll_visible=False)
        self.cnt["reasoning"].display = False
        self.app.refresh_bindings()

    def action_remove(self) -> None:
        if not self.is_removing:
            self.is_removing = True
            self.chat_view.is_removing = True
            self.chat_view.post_message(RemoveMessage(self.chat.message_index(self.message)))

    async def action_add_content(self) -> None:
        content = {"type": "text", "text": ""}
        await self.maybe_mount_content("content")
        if not "content" in self.message:
            self.message["content"] = [content]
        else:
            self.message["content"].append(content)
        await self.cnt["content"].mount(Process(self.chat, self, "content"))
        process = self.cnt["content"].children[-1]
        process.edit = TextAreaEdit(process, True)
        self.is_edit += 1
        process.is_edit = True
        await process.mount(process.edit)

    async def action_add_reasoning(self) -> None:
        await self.maybe_mount_content("reasoning")
        if not "reasoning" in self.message:
            self.message["reasoning"] = ""
        await self.cnt["reasoning"].mount(Process(self.chat, self, "reasoning"))
        process = self.cnt["reasoning"].children[0]
        process.edit = TextAreaEdit(process, True)
        self.is_edit += 1
        process.is_edit = True
        await process.mount(process.edit)

    async def action_add_tool(self) -> None:
        hash_id = self.app.get_rand_seq(32)
        name = self.chat.cs("tools")[0]
        await self.maybe_mount_content("tool_calls")
        function = {"id": hash_id, "type": "function", "function": {"name": name, "arguments": "{}"}}
        if not "tool_calls" in self.message:
            self.message["tool_calls"] = [function]
        else:
            self.message["tool_calls"].append(function)
        await self.cnt["tool_calls"].mount(Process(self.chat, self, "tool_calls"))
        process = self.cnt["tool_calls"].children[-1]
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
        # The dict goes into the data first, then `mount_message` is asked for
        # the widget and hands it back: at either window edge that is a
        # `materialize` (an insert below the top slides lo +1, an insert at or
        # above the bottom closes a pruned end), where the bare mount that stood
        # here appended behind the wrong neighbour and the `require_widget`
        # after it raised with the data already changed. Taking the returned
        # widget instead of looking the same index up twice is WP-E's deviation
        # from the plan's wording: the guarantee and the lookup are one call.
        widget = await self.chat_view.mount_message(index)
        await widget.status.update("")
        self.chat.write_chat_history()
        widget.focus()

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
        # Same as `add_message_next`: `mount_message(0)` guarantees a widget at
        # 0 whatever the window looked like. `check_action` only lets this
        # binding run with `message_index == 0`, so the widget it is bound to is
        # mounted and lo is 0 - the in-window neighbour mount; the branch is
        # still written for the window, not for that argument.
        widget = await self.chat_view.mount_message(0)
        await widget.status.update("")
        if self.role == "tool":
            await widget.finish()
        self.chat.write_chat_history()
        widget.focus()

    def has_reasoning(self) -> bool:
        if self.message["role"] == "assistant" and self.message["reasoning"]:
            return True
        return False

    def maybe_add_message_next(self) -> None:
        # The NEXT MESSAGE'S ROLE, read from the data. The old line was
        # `require_widget(index+1)`, and this runs from `check_action` - which
        # `refresh_bindings` calls with nobody pressing anything - so once the
        # bottom had been pruned and focus sat on the last mounted widget the
        # whole binding pass raised IndexError out of Textual's machinery
        # (measured: window (950, 957) with focus on child[6], widget(158) is
        # None, `check_action("add_message_next")` -> IndexError).
        # `refresh_bindings` runs on every worker-state change, so this was a
        # crash with NO keypress. The question was never about a widget - it
        # asks what role the message AFTER this one has - and the line above
        # already proved `index` is not the last message, so the data has it.
        # The answer is now the SAME whether or not the neighbour is mounted.
        index = self.chat.message_index(self.message)
        if len(self.messages)-1 == index:
            return True
        next_role = self.messages[index + 1]["role"]
        if self.role == "assistant" and "tool_calls" in self.message and self.message["tool_calls"]:
            if not next_role == "tool":
                return True
        elif self.role == "assistant":
            if not next_role == "user":
                return True
        elif self.role == "tool" and not next_role == "assistant":
            return True
        elif self.role == "user" and not next_role == "assistant":
            return True
        return False

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.is_removing or self.chat_view.is_removing:
            return False
        if action == "show_cot":
            if self.chat_view.is_edit:
                return False
            if not "reasoning" in self.cnt:
                return False
            if self.cnt["reasoning"].display:
                return False
        elif action == "hide_cot":
            if self.chat_view.is_edit:
                return False
            if not "reasoning" in self.cnt:
                return False
            if not self.cnt["reasoning"].display:
                return False
        elif action == "remove":
            if self.chat.is_working() or self.is_edit or not self.chat_view.is_edit:
                return False
        elif action == "add_content":
            if not self.chat_view.is_edit:
                return False
        elif action == "add_reasoning":
            if not self.chat_view.is_edit or not self.role == "assistant":
                return False
            if "reasoning" in self.cnt and self.cnt["reasoning"]:
                return False
        elif action == "add_tool":
            if not self.role == "assistant" or not self.chat_view.is_edit or not self.chat.cs("tools"):
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
        await self.cnt[message.scontent].children[message.index].remove()
        if type(self.message[message.scontent]) is list:
            del self.message[message.scontent][message.index]
            if self.message[message.scontent]:
                self.chat.write_chat_history()
                return None
            await self.cnt[message.scontent].remove()
            del self.cnt[message.scontent]
            if not message.scontent == "content":
                del self.message[message.scontent]
        else:
            del self.message[message.scontent]
            await self.cnt[message.scontent].remove()
            del self.cnt[message.scontent]
        self.chat.write_chat_history()

    async def on_reset_process(self, message: ResetProcess) -> None:
        if not message.text is None:
            async with self.cnt[message.scontent].children[message.index].batch():
                await self.cnt[message.scontent].children[message.index].reset()
                await self.cnt[message.scontent].children[message.index].finish(message.text)
        else:
            await self.cnt[message.scontent].children[message.index].remove()
            del self.message[message.scontent][message.index]
            if not self.message[message.scontent] and not message.scontent == "content":
                await self.cnt[message.scontent].remove()
                del self.cnt[message.scontent]
                del self.message[message.scontent]
        self.app.refresh_bindings()
