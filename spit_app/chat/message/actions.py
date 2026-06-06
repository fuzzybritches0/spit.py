import json

bindings = [
    ("s", "show_cot", "Show CoT"),
    ("s", "hide_cot", "Hide CoT"),
    ("x", "remove", "Remove")
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

    async def action_remove(self) -> None:
        index = self.messages.index(self.message)
        self.chat.undo.append_undo("remove", self.message, index)
        del self.messages[index]
        self.chat.write_chat_history()
        if len(self.chat.chat_view.children) > 1:
            self.chat.chat_view.children[-2].focus(scroll_visible=False)
        await self.remove()

    def has_reasoning(self) -> bool:
        if self.message["role"] == "assistant" and self.message["reasoning"]:
            return True
        return False

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if ((self.chat.is_working() or self.chat.text_area.is_edit) and
            not (action == "show_cot" or action == "hide_cot")):
            return False
        match action:
            case "show_cot":
                if not "reasoning" in self.pr:
                    return False
                if self.pr["reasoning"].display:
                    return False
            case "hide_cot":
                if not "reasoning" in self.pr:
                    return False
                if not self.pr["reasoning"].display:
                    return False
            case "remove":
                if not self.chat.chat_view.children:
                    return False
        return True
