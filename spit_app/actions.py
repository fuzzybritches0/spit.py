# SPDX-License-Identifier: GPL-2.0

bindings = [
        ("ctrl+q", "exit_app", "Quit"),
        ("shift+escape", "side_panel", "Side Panel")
]

class ActionsMixIn:
    async def action_side_panel(self) -> None:
        chat_list = self.query_one("#side-panel")
        if not chat_list is self.focused:
            chat_list.display = True
            chat_list.disable = False
            chat_list.focus()
        else:
            chat_list.display = False
            chat_list.disable = True
            index = 0
            for child in self.query_one("#main").children:
                if child.display:
                    self.focus_first(index)
                    break
                index+=1

    def action_exit_app(self) -> None:
        self.exit()
