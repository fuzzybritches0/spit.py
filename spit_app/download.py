import os
import httpx
import asyncio
from pathlib import Path
from spit_app.modal_screens import ProgressBarScreen
from spit_app.textual_message import DownloadFailed, DownloadSuccess

class Download:
    def __init__(self, app) -> None:
        self.app = app
        self.run_worker = app.run_worker
        self.push_screen = app.push_screen
        self.settings = app.settings
        self.working = False
        self.cancel = False
        self.pending = []
        self.progress_bar_screen = None
        self.progress_state_reset()

    def progress_state_reset(self) -> None:
        self.progress_state = {"text": "Connecting...", "total": 0, "progress": 0}

    def progress_update(self, key: str, value: str|int) -> None:
        if self.progress_bar_screen:
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

    async def cancel_work(self) -> None:
        if self.working:
            self.cancel = True
            while self.working:
                await asyncio.sleep(.1)
            self.pending = []
        await self.progress_dismiss()
        self.progress_state_reset()

    async def progress_dismiss(self) -> None:
        if self.progress_bar_screen:
            await self.progress_bar_screen.dismiss()
            self.progress_bar_screen = None

    def show_progress(self) -> None:
        self.progress_bar_screen = ProgressBarScreen(self)
        self.push_screen(self.progress_bar_screen)

    def download(self, sender, lst: list, callback: str) -> None:
        self.pending.append((sender, lst, callback))
        if not self.progress_bar_screen:
            self.show_progress()
        if not self.working:
            self.run_worker(self.work_download())

    async def work_download(self) -> None:
        self.working = True
        while self.pending:
            self.progress_state_reset()
            success = True
            sender, lst, callback = self.pending[0]
            count = 1
            total = len(lst)
            for url, path in lst:
                if self.progress_bar_screen:
                    file = str(path).split("/")[-1]
                    self.progress_update("text", f"Downloading {count} of {total}:\n{file}")
                if not await self.try_download(url, path):
                    success = False
                    break
                count += 1
            if success:
                sender.post_message(DownloadSuccess(lst, callback))
            else:
                sender.post_message(DownloadFailed(lst, callback))
            if self.pending:
                del self.pending[0]
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
                    return False
                length = 0
                if "Content-Length" in resp.headers:
                    length = int(resp.headers["Content-Length"])
                self.progress_update("total", length+size)
                if not self.check_size(path, length+size):
                    file = str(path).split("/")[-1]
                    e = f"Size of {file} changed on server! Please delete model and re-download!"
                    self.exception = Exception(e)
                    return False
                self.progress_update("progress", size)
                async for binary in resp.aiter_bytes():
                    if self.cancel:
                        self.cancel = False
                        self.working = False
                        return False
                    self.progress_update("progress", len(binary))
                    with open(path, "ab") as f:
                        f.write(binary)
        return True
