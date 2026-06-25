# SPDX-License-Identifier: GPL-2.0
import os
import shutil
import getpass
import asyncio
import signal
from pathlib import Path

SANDBOX_ENV = "/".join(__file__.split("/")[:-1]) + "/sandbox_env.sh"

def get_script(tool, common: str = "") -> str:
    ret = ""
    script_dir = "/".join(tool.split("/")[0:-1])
    script = tool.split("/")[-1]
    script_path = script_dir + "/scripts/" + script
    if common:
        common_path = script_dir + "/scripts/common/" + common + ".py"
        with open(common_path, "r") as f:
            common = f.read() + "\n"
    with open(script_path, "r") as f:
        return common + f.read()

class Run:
    def __init__(self, app, chat_id: str, cmd: str, script: str,
                 sandbox: bool = True, timeout: int = 0):
        sandbox_home = app.query_one("#main").query_one(f"#{chat_id}").cs("sandbox")
        self.sandbox_path = app.settings.path["sandbox"] / sandbox_home
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        self.cmd = [cmd]
        self.script = script
        self.sandbox = sandbox
        self.timeout = timeout

    def bwrap_args(self, user: str) -> list:
        nobind = ["dev", "proc", "boot", "home"]
        args = ["bwrap"]
        for d in os.listdir("/"):
            if not d in nobind:
                args += ["--bind", f"/{d}", f"/{d}"]
        args += ["--setenv", "PIP_BREAK_SYSTEM_PACKAGES", "True"]
        args += ["--setenv", "PIP_USER", "True"]
        args += ["--chdir", f"/home/{user}"]
        args += ["--bind", self.sandbox_path, f"/home/{user}"]
        args += ["--bind", SANDBOX_ENV, f"/home/{user}/.sandbox_env.sh"]
        args += ["--unshare-all", "--share-net", "--proc", "/proc",
                 "--dev", "/dev", "--new-session"]
        return args

    async def run(self):
        user = getpass.getuser()
        if self.sandbox and not shutil.which("bwrap"):
            yield "ERROR: `bwrap` not found! Give user instructions to install `bubblewrap`!"
            return
        if not shutil.which(self.cmd[0]):
            yield f"ERROR: `{self.cmd[0]}` not found!"
            return
        if self.sandbox:
            cmd_args = self.bwrap_args(user) + [f"/home/{user}/.sandbox_env.sh"] + self.cmd
        else:
            cmd_args = [SANDBOX_ENV] + self.cmd
        proc = await asyncio.create_subprocess_exec(*cmd_args,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        cwd=self.sandbox_path, start_new_session=True)
        proc.stdin.write(self.script.encode())
        await proc.stdin.drain()
        proc.stdin.close()
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
                yield "\nERROR: Terminated! Execution exceeded timeout limit!"
                return
        else:
            while True:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    break
                yield line_bytes.decode("UTF-8", errors="replace")
        return_code = await proc.wait()
        yield f"\nProcess exited with code {return_code}."
