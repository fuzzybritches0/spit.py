# SPDX-License-Identifier: GPL-2.0

bindings = [
        ("ctrl+q", "exit_app", "Quit"),
        ("shift+escape", "side_panel", "Side Panel")
]

class ActionsMixIn:
    async def action_side_panel(self) -> None:
        side_panel = self.query_one("#side-panel")
        if not side_panel is self.focused:
            side_panel.display = True
            side_panel.disable = False
            side_panel.can_focus = True
            side_panel.focus()
        else:
            side_panel.can_focus = False
            side_panel.display = False
            side_panel.disable = True
            index = 0
            for child in self.query_one("#main").children:
                if child.display:
                    self.focus_first(index)
                    break
                index+=1

    def action_exit_app(self) -> None:
        self.exit()
