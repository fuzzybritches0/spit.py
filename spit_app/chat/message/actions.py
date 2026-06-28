import json
from spit_app.chat.textual_message import RemoveMessage

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

    def action_remove(self) -> None:
        if not self.is_removing:
            self.is_removing = True
            self.chat_view.post_message(RemoveMessage(self.chat_view.children.index(self)))

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
            if self.chat.is_working() or self.is_edit:
                return False
            if not self.chat_view.is_edit:
                return False
        return True
