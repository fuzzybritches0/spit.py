# SPDX-License-Identifier: GPL-2.0
from textual import work
from textual.binding import Binding
from .modal_screens import ConfirmScreen

bindings = [
        Binding("ctrl+q", "exit_app", "Quit", show=False),
        ("shift+escape", "side_panel", "Side Panel")
]

class ActionsMixIn:
    async def action_side_panel(self) -> None:
        side_panel = self.query_one("#side-panel")
        if not side_panel is self.focused:
            side_panel.display = True
            side_panel.can_focus = True
            side_panel.focus()
        else:
            side_panel.can_focus = False
            side_panel.display = False
            index = 0
            for child in self.query_one("#main").children:
                if child.display:
                    child.focus()
                    break
                index+=1

    @work
    async def action_exit_app(self) -> None:
        if await self.push_screen_wait(ConfirmScreen()):
            self.exit()
