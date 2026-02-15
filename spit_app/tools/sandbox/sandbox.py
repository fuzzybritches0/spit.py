# SPDX-License-Identifier: GPL-2.0
import os
import shutil
import getpass
import asyncio
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

    def preflight_test(self) -> str:
        ret = ""
        if not shutil.which("bwrap"):
            ret += "ERROR: `bwrap` not found! Give user instructions to install `bubblewrap`!\n"
        if self.timeout and not shutil.which("timeout"):
            ret += "ERROR: `timeout` not found! Give user instructions to install `timeout`!"
        if ret:
            return ret
        return None

    async def run_sandbox(self):
        ret = self.preflight_test()
        if ret:
            yield ret
        else:
            cmd_args = self.bwrap_args() + self.cmd_args
            proc = await asyncio.create_subprocess_exec(*cmd_args, stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.STDOUT,
                                                    cwd=self.sandbox_path)
            yield "```\n"
            while True:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    break
                yield line_bytes.decode("UTF-8", errors="replace")
            if proc and proc.returncode is None:
                proc.terminate()
                await proc.wait()
            yield "\n```"
