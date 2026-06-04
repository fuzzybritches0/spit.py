# SPDX-License-Identifier: GPL-2.0
import asyncio
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
        if self.confirm_exit:
            return None
        self.confirm_exit = True
        if await self.push_screen_wait(ConfirmScreen()):
            self.terminate = True
            for cont in self.query_one("#main").children:
                if cont.id.startswith("chat-"):
                    while cont.chat_view.working:
                        await asyncio.sleep(1)
                await cont.remove()
            self.exit()
        self.confirm_exit = False

    def clean_exit(self) -> None:
        self.chats-=1
        if not self.chats:
            self.exit()
