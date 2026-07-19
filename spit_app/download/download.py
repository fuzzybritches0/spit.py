import os
import httpx
import asyncio
import inspect
from pathlib import Path
from spit_app.modal_screens import ProgressBarScreen
from spit_app.textual_message import DownloadFailed, DownloadSuccess
from .post_download_methods import PostDownloadMethods as pdm

class Download:
    def __init__(self, app) -> None:
        self.app = app
        self.run_worker = app.run_worker
        self.push_screen = app.push_screen
        self.settings = app.settings
        self.working = False
        self.cancel = False
        self.clear = False
        self.exception = None
        self.pending = []
        self.progress_bar_screen = None
        self.progress_state_reset()

    def progress_is_active(self) -> bool:
        if self.progress_bar_screen and self.progress_bar_screen.is_active:
            return True
        return False

    def progress_state_reset(self) -> None:
        self.progress_state = {"text": "Connecting...", "total": 0, "progress": 0}
        if self.progress_is_active():
            self.progress_bar_screen.reset()

    def progress_update(self, key: str, value: str|int) -> None:
        if self.progress_is_active():
            if key == "text":
                self.progress_bar_screen.update_text(value)
            elif key == "total":
                self.progress_bar_screen.update_total(value)
            elif key == "progress":
                self.progress_bar_screen.update_progress(value)
        if key == "progress":
            self.progress_state[key] += value
        else:
            self.progress_state[key] = value

    async def cancel_work(self, clear: bool = False) -> None:
        self.clear = clear
        if self.working:
            self.cancel = True
            while self.working:
                await asyncio.sleep(.1)
        await self.progress_dismiss()
        self.progress_state_reset()

    async def progress_dismiss(self) -> None:
        if self.progress_is_active():
            await self.progress_bar_screen.dismiss()
            self.progress_bar_screen = None

    def show_progress(self) -> None:
        self.progress_bar_screen = ProgressBarScreen(self)
        self.push_screen(self.progress_bar_screen)

    def download(self, sender_id: str, name: str, lst: list, callback: str) -> None:
        self.pending.append((sender_id, name, lst, callback))
        if not self.progress_is_active():
            self.show_progress()
        if not self.working:
            self.run_worker(self.work_download())

    def callback_sender(self, sender_id: str, callback: str, lst: list, success: bool) -> None:
        for cont in self.app.query_one("#main").children:
            if cont.id == sender_id:
                if success:
                    cont.post_message(DownloadSuccess(callback))
                else:
                    cont.post_message(DownloadFailed(callback))
                return None

    async def post_download_method(self, callback: str, lst: list, success: bool) -> None:
        add = "failed"
        if success:
            add = "success"
        if hasattr(pdm, f"{callback}_{add}"):
            method = getattr(pdm, f"{callback}_{add}")
            if inspect.iscoroutinefunction(method):
                await method(self.app, lst)
            else:
                method(self.app, lst)

    async def work_download(self) -> None:
        self.working = True
        while self.pending:
            self.progress_state_reset()
            success = True
            sender_id, name, lst, callback = self.pending[0]
            count = 1
            total = len(lst)
            for url, path in lst:
                self.progress_state_reset()
                if self.progress_is_active():
                    file = str(path).split("/")[-1]
                    self.progress_update("text", f"Downloading {count} of {total}:\n{file}")
                try:
                    if not await self.try_download(url, path):
                        success = False
                        break
                except Exception as exception:
                    if type(exception).__name__ in ("ReadTimeout", "ConnectTimeout"):
                        self.exception = exception
                        success = False
                        break
                    else:
                        raise self.exception
                count += 1
            if success:
                del self.pending[0]
                await self.post_download_method(callback, lst, True)
                self.app.action_notify(f"Download finished for {name}")
                self.callback_sender(sender_id, callback, lst, True)
            else:
                await self.post_download_method(callback, lst, False)
                self.app.action_notify(f"Download failed for {name}")
                self.callback_sender(sender_id, callback, lst, False)
                if self.cancel:
                    self.cancel = False
                    if self.clear:
                        self.pending = []
                        self.clear = False
                    self.working = False
                    await self.progress_dismiss()
                    if self.exception:
                        self.app.exception = self.exception
                        self.exception = None
                    return None
        self.working = False
        await self.progress_dismiss()

    def check_size(self, path: Path, size: int) -> bool:
        if not "downloads" in self.settings.llamacpp:
            self.settings.llamacpp["downloads"] = []
        for download in self.settings.llamacpp["downloads"]:
            if download["path"] == str(path):
                if size == download["size"]:
                    return True
                else:
                    return False
        self.settings.llamacpp["downloads"].append({"path": str(path), "size": size})
        self.settings.save()
        return True

    async def try_download(self, url: str, path: Path) -> bool:
        headers = {}
        size = 0
        if os.path.exists(path):
            size = os.path.getsize(path)
        if size > 0:
            headers = {
                "Range": f"bytes={size}-",
            }
        async with httpx.AsyncClient(timeout=15) as client:
            async with client.stream("GET", url, follow_redirects=True, headers=headers) as resp:
                if resp.status_code == 416:
                    return True
                if not resp.status_code == 200 and not resp.status_code == 206:
                    await self.progress_dismiss()
                    self.exception = Exception(str(resp))
                    return False
                length = 0
                if "Content-Length" in resp.headers:
                    length = int(resp.headers["Content-Length"])
                self.progress_update("total", length+size)
                if not self.check_size(path, length+size):
                    file = str(path).split("/")[-1]
                    e = f"Size of {file} changed on server!"
                    os.remove(path)
                    self.app.del_downloads_size([str(path)])
                    await self.progress_dismiss()
                    self.app.exception = Exception(e)
                    return False
                self.progress_update("progress", size)
                async for binary in resp.aiter_bytes():
                    if self.cancel:
                        return False
                    self.progress_update("progress", len(binary))
                    with open(path, "ab") as f:
                        f.write(binary)
        return True
