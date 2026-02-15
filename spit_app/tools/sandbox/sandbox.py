# SPDX-License-Identifier: GPL-2.0
import os
import shutil
import getpass
import asyncio
import signal
from pathlib import Path

class Sandbox:
    def __init__(self, sandbox_path: Path, cmd_args: list, timeout: int = 0):
        self.sandbox_path = sandbox_path
        self.cmd_args = cmd_args
        self.timeout = timeout

    def bwrap_args(self) -> list:
        user = getpass.getuser()
        nobind = ["dev", "proc", "boot", "home", "tmp"]
        args = ["bwrap"]
        for d in os.listdir("/"):
            if not d in nobind:
                args += ["--bind", f"/{d}", f"/{d}"]
        args += ["--chdir", f"/home/{user}"]
        args += ["--bind", self.sandbox_path, f"/home/{user}"]
        args += ["--share-net", "--unshare-all", "--proc", "/proc",
                 "--dev", "/dev", "--tmpfs", "/tmp", "--new-session"]
        return args

    async def run_sandbox(self):
        if not shutil.which("bwrap"):
            yield "ERROR: `bwrap` not found! Give user instructions to install `bubblewrap`!"
            return
        cmd_args = self.bwrap_args() + self.cmd_args
        proc = await asyncio.create_subprocess_exec(*cmd_args, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.STDOUT,
                                                cwd=self.sandbox_path, start_new_session=True)
        yield "```\n"
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
                yield "\n```"
                yield "\nTIMEOUT: execution exceeded timeout limit!"
                return
        else:
            while True:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    break
                yield line_bytes.decode("UTF-8", errors="replace")
        return_code = await proc.wait()
        yield "\n```"
        yield f"\nProcess exited with code {return_code}."
