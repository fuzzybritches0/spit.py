# SPDX-License-Identifier: GPL-2.0
import os
from spit_app.chat.chat import Chat

class HandlersMixIn:
    async def on_theme_changed(self, old_value:str, new_value:str) -> None:
        self.settings.theme = self.theme
        self.settings.save()

    async def on_ready(self) -> None:
        if self.settings.active_chat:
            active = self.settings.active_chat
            filename = active + ".json"
            if os.path.exists(self.path["chats"] / filename):
                await self.app.query_one("#main").mount(Chat(active))
                index = self.query_one("#side-panel").get_option_index(active)
                self.query_one("#side-panel").highlighted = index
            else:
                self.query_one("#side-panel").highlighted = 0
