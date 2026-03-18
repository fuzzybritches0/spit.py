import json

bindings = [
    ("e", "edit", "Edit"),
]

class ActionsMixIn:
    def action_edit(self) -> None:
        self.chat.text_area.temp = self.chat.text_area.text
        if self.scontent == "tool_calls":
            self.chat.text_area.text = json.dumps(self.message.message[self.scontent])
        else:
            if type(self.message.message[self.scontent]) is str:
                self.chat.text_area.text = self.message.message[self.scontent]
            else:
                self.chat.text_area.text = self.message.message[self.scontent][self.count]["text"]
        self.chat.text_area.is_edit = True
        self.chat.text_area.scontent = self.scontent
        self.chat.text_area.scontent_count = self.count
        self.chat.text_area.edit_container = self.message
        self.chat.text_area.focus()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.chat.is_working() or self.chat.text_area.is_edit:
            return False
        return True
