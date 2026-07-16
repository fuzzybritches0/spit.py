import os
import httpx
import asyncio
from pathlib import Path
from spit_app.modal_screens import ProgressBarScreen
from spit_app.textual_message import DownloadFailed, DownloadSuccess

class Download:
    def __init__(self, run_worker: callable, push_screen: callable) -> None:
        self.run_worker = run_worker
        self.push_screen = push_screen
        self.working = False
        self.cancel = False
        self.pending = []
        self.progress_bar_screen = None

    async def cancel_work(self) -> None:
        if self.working:
            self.cancel = True
            while self.working:
                await asyncio.sleep(.1)
            self.pending = []
        await self.progress_dismiss()

    def progress_active(self) -> bool:
        if self.progress_bar_screen and self.progress_bar_screen.is_active:
            return True
        return False

    async def progress_dismiss(self) -> None:
        if self.progress_active():
            await self.progress_bar_screen.dismiss()
            self.progress_bar_screen = None

    def show_progress(self) -> None:
        self.progress_bar_screen = ProgressBarScreen(self)
        self.push_screen(self.progress_bar_screen)

    def download(self, sender, lst: list, callback: str) -> None:
        self.pending.append((sender, lst, callback))
        if not self.progress_active():
            self.show_progress()
        if not self.working:
            self.run_worker(self.work_download())

    async def work_download(self) -> None:
        self.working = True
        while self.pending:
            success = True
            sender, lst, callback = self.pending[0]
            count = 1
            total = len(lst)
            for url, path in lst:
                if self.progress_active():
                    file = str(path).split("/")[-1]
                    self.progress_bar_screen.update_text(f"Downloading {count} of {total}:\n{file}")
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

    async def try_download(self, url: str, path: Path) -> bool:
        headers = {}
        size = 0
        if os.path.exists(path):
            size = os.path.getsize(path)
        if size > 0:
            headers = {
                "Range": f"bytes={size}-",
            }
        if self.progress_active():
            self.progress_bar_screen.update_progress(size)
        async with httpx.AsyncClient(timeout=15) as client:
            async with client.stream("GET", url, follow_redirects=True, headers=headers) as resp:
                if resp.status_code == 416:
                    return True
                if not resp.status_code == 200 and not resp.status_code == 206:
                    return False
                length = -1
                downloaded = 0
                if "Content-Length" in resp.headers:
                    length = int(resp.headers["Content-Length"])
                    if length == size:
                        if self.progress_active():
                            self.progress_bar_screen.update_total(length)
                        return True
                if length > 0:
                    if self.progress_active():
                        self.progress_bar_screen.update_total(length)
                async for binary in resp.aiter_bytes():
                    if self.cancel:
                        self.cancel = False
                        self.working = False
                        return False
                    if self.progress_active():
                        self.progress_bar_screen.update_progress(len(binary))
                    with open(path, "ab") as f:
                        f.write(binary)
        return True
