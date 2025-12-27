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
            file_name = active + ".json"
            if os.path.exists(self.settings.data_path / file_name):
                index = self.query_one("#side-panel").get_option_index(active)
                self.query_one("#side-panel").highlighted = index
                await self.query_one("#main").mount(Chat(active))
            else:
                self.settings.active_chat = None
                self.settings.save()
