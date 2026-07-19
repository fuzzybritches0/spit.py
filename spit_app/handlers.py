# SPDX-License-Identifier: GPL-2.0
import os
from textual.events import AppFocus, AppBlur
from .textual_message import DownloadFiles
from spit_app.chat.chat import Chat
from .modal_screens import CancelWork

class HandlersMixIn:
    async def on_theme_changed(self, old_value:str, new_value:str) -> None:
        self.settings.theme = self.theme
        self.settings.save()

    async def on_ready(self) -> None:
        if "pending" in self.settings.downloads and self.settings.downloads["pending"]:
            self.download.pending = self.settings.downloads["pending"]
            if self.settings.downloads["working"]:
                self.run_worker(self.download.work_download())
            self.settings.save()
            self.refresh_bindings()
        if self.settings.active_chat:
            active = self.settings.active_chat
            filename = active + ".json"
            if os.path.exists(self.path["chats"] / filename):
                await self.app.query_one("#main").mount(Chat(active))
                await self.app.query_one("#main").query_one(f"#{active}").chat_view.load()
                return None
        self.settings.active_chat = None
        self.settings.save()
        self.query_one("#side-panel").highlighted = 0

    def on_app_focus(self, event: AppFocus) -> None:
        event.prevent_default()

    def on_app_blur(self, event: AppBlur) -> None:
        event.prevent_default()

    def on_download_files(self, message: DownloadFiles) -> None:
        self.download.download(message.sender_id, message.name, message.lst, message.callback)

    def on_worker_state_changed(self) -> None:
        self.refresh_bindings()

    async def on_progress_dismiss(self) -> None:
        await self.download.progress_dismiss()

    async def on_cancel_work(self, message: CancelWork) -> None:
        await self.download.cancel_work(message.clear)
