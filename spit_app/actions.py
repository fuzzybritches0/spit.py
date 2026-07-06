# SPDX-License-Identifier: GPL-2.0
from textual import work
from .modal_screens import ConfirmScreen

bindings = [
        ("ctrl+q", "exit_app"),
        ("shift+escape", "side_panel", "S.Panel")
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
        if self.confirm_exit:
            return None
        self.confirm_exit = True
        if await self.push_screen_wait(ConfirmScreen()):
            for cont in self.query_one("#main").children:
                await cont.remove()
            self.exit()
        self.confirm_exit = False
