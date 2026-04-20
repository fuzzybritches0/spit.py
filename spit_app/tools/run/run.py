# SPDX-License-Identifier: GPL-2.0
import os
import shutil
import getpass
import asyncio
import signal
from pathlib import Path

class Run:
    def __init__(self, app, chat_id: str, cmd: str, script: str,
                 sandbox: bool = True, timeout: int = 0):
        sandbox_home = app.query_one("#main").query_one(f"#{chat_id}").csettings["sandbox"]["value"]
        self.sandbox_path = app.settings.path["sandbox"] / sandbox_home
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        self.cmd = [cmd]
        self.script = script
        self.sandbox = sandbox
        self.timeout = timeout

    def bwrap_args(self) -> list:
        user = getpass.getuser()
        nobind = ["dev", "proc", "boot", "home", "tmp"]
        args = ["bwrap"]
        for d in os.listdir("/"):
            if not d in nobind:
                args += ["--bind", f"/{d}", f"/{d}"]
        args += ["--setenv", "PIP_BREAK_SYSTEM_PACKAGES", "True"]
        args += ["--setenv", "PIP_USER", "True"]
        args += ["--chdir", f"/home/{user}"]
        args += ["--bind", self.sandbox_path, f"/home/{user}"]
        args += ["--unshare-all", "--share-net", "--proc", "/proc",
                 "--dev", "/dev", "--tmpfs", "/tmp", "--new-session"]
        return args

    async def run(self):
        if self.sandbox and not shutil.which("bwrap"):
            yield "ERROR: `bwrap` not found! Give user instructions to install `bubblewrap`!"
            return
        if not shutil.which(self.cmd[0]):
            yield f"ERROR: `{self.cmd[0]}` not found!"
            return
        cmd_args = self.cmd
        if self.sandbox:
            cmd_args = self.bwrap_args() + self.cmd
        proc = await asyncio.create_subprocess_exec(*cmd_args,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        cwd=self.sandbox_path, start_new_session=True)
        proc.stdin.write(self.script.encode())
        await proc.stdin.drain()
        proc.stdin.close()
        yield "~~~~\n"
        if self.timeout > 0:
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
                for line in stdout.decode("UTF-8", errors="replace").splitlines(keepends=True):
                    yield line
            except:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                yield "\n~~~~"
                yield "\nTIMEOUT: execution exceeded timeout limit!"
                return
        else:
            while True:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    break
                yield line_bytes.decode("UTF-8", errors="replace")
        return_code = await proc.wait()
        yield "\n~~~~"
        yield f"\nProcess exited with code {return_code}."
