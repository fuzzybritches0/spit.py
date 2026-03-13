import json

bindings = [
    ("s", "show_cot", "Show CoT"),
    ("s", "hide_cot", "Hide CoT"),
    ("e", "edit_content", "Edit content"),
    ("c", "edit_cot", "Edit CoT"),
    ("t", "edit_tool", "Edit tool call"),
    ("x", "remove_last", "Remove turn")
]

class ActionsMixIn:
    def action_show_cot(self) -> None:
        self.pr["reasoning"].display = True
        self.app.refresh_bindings()

    def action_hide_cot(self) -> None:
        self.pr["reasoning"].display = False
        self.app.refresh_bindings()

    def action_edit_content(self) -> None:
        self.edit_message("content")

    def action_edit_cot(self) -> None:
        self.edit_message("reasoning")

    def action_edit_tool(self) -> None:
        self.edit_message("tool_calls")

    async def action_remove_last(self) -> None:
        self.chat.undo.append_undo("remove", self.message)
        del self.messages[-1]
        self.chat.write_chat_history()
        if len(self.chat.chat_view.children) > 1:
            self.chat.chat_view.children[-2].focus(scroll_visible=False)
        await self.remove()

    def edit_message(self, ctype: str) -> None:
        self.chat.text_area.temp = self.chat.text_area.text
        if ctype == "tool_calls":
            self.chat.text_area.text = json.dumps(self.message[ctype])
        else:
            self.chat.text_area.text = self.message[ctype]
        self.chat.text_area.is_edit = True
        self.chat.text_area.ctype = ctype
        self.chat.text_area.edit_container = self
        self.chat.text_area.focus()

    def has_reasoning(self) -> bool:
        if self.message["role"] == "assistant" and self.message["reasoning"]:
            return True
        return False

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        if not self is self.app.focused:
            return False
        if ((self.chat.is_working() or self.chat.text_area.is_edit) and
            not (action == "show_cot" or action == "hide_cot")):
            return False
        match action:
            case "show_cot":
                if not self.has_reasoning():
                    return False
                if self.pr["reasoning"].display:
                    return False
            case "hide_cot":
                if not self.has_reasoning():
                    return False
                if not self.pr["reasoning"].display:
                    return False
            case "edit_content":
                if not self.message["content"]:
                    return False
            case "edit_cot":
                if not self.has_reasoning():
                    return False
            case "edit_tool":
                if not "tool_calls" in self.message:
                    return False
            case "remove_last":
                if not self.parent.children:
                    return False
                if not self is self.parent.children[-1]:
                    return False
        return True
