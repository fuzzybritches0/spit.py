# SPDX-License-Identifier: GPL-2.0
import os
import shutil
import getpass
import asyncio
import signal
import libtmux
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
    def __init__(self, app, chat_id: str, cmd: str, script: str, sandbox: bool = True, timeout: int = 0) -> None:
        self.tmux = app.tmux
        self.chat_id = chat_id
        self.get_rand_seq = app.get_rand_seq
        sandbox_home = app.query_one("#main").query_one(f"#{chat_id}").cs("sandbox")
        self.sandbox_path = app.settings.path["sandbox"] / sandbox_home
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        self.sandbox_tmp = app.settings.path["sandbox_tmp"] / sandbox_home
        self.sandbox_tmp.mkdir(parents=True, exist_ok=True)
        self.sandbox_path = str(self.sandbox_path)
        self.sandbox_tmp = str(self.sandbox_tmp)
        self.cmd = [cmd]
        self.script = script
        self.sandbox = sandbox
        self.timeout = timeout
        self.timeout_reached = False
        self.terminated = False
        self.chat = app.query_one("#main").query_one(f"#{chat_id}")

    def bwrap_args(self, user: str) -> list:
        nobind = ["dev", "proc", "boot", "home", "tmp"]
        args = ["bwrap"]
        for d in os.listdir("/"):
            if not d in nobind:
                args += ["--bind", f"/{d}", f"/{d}"]
        args += ["--die-with-parent"]
        args += ["--setenv", "PIP_BREAK_SYSTEM_PACKAGES", "True"]
        args += ["--setenv", "PIP_USER", "True"]
        args += ["--chdir", f"/home/{user}"]
        args += ["--bind", self.sandbox_path, f"/home/{user}"]
        args += ["--bind", self.sandbox_tmp, f"/tmp"]
        args += ["--bind", SANDBOX_ENV, f"/home/{user}/.sandbox_env.sh"]
        args += ["--unshare-all", "--share-net", "--proc", "/proc", "--dev", "/dev"]
        return args

    def term_new(self) -> str:
        user = getpass.getuser()
        if self.sandbox and not shutil.which("bwrap"):
            return "ERROR: `bwrap` not found! Give user instructions to install `bubblewrap`!"
        if not shutil.which("bash"):
            return "ERROR: `bash` not found!"
        if self.sandbox:
            cmd_args = self.bwrap_args(user) + ["bash"]
        else:
            cmd_args = [SANDBOX_ENV] + ["bash"]
        cmd_args = " ".join(cmd_args)
        if not self.chat_id in self.tmux:
            self.tmux[self.chat_id] = {}
            self.tmux[self.chat_id]["server"] = libtmux.Server()
            self.tmux[self.chat_id]["session"] = self.tmux[self.chat_id]["server"].new_session()
            self.tmux[self.chat_id]["window"] = self.tmux[self.chat_id]["session"].new_window(attach=True)
            self.tmux[self.chat_id]["panes"] = {}
        window = self.tmux[self.chat_id]["window"]
        panes = self.tmux[self.chat_id]["panes"]
        idx = self.get_rand_seq(8)
        panes[idx] = window.split(attach=True, shell=cmd_args, percentage=100)
        return f"Terminal session created. Access token: {idx}"

    def term_send_keys(self, idx: str, keys: str, enter: bool, literal: bool) -> str:
        panes = self.tmux[self.chat_id]["panes"]
        if not idx in panes:
            return f"ERROR: {idx} does not exist!"
        if panes[idx].pane_dead == "1":
            del panes[idx]
            return f"{idx} is dead!"
        panes[idx].send_keys(keys, enter=enter, literal=literal)
        return "OK"

    def term_screen(self, idx: str) -> str:
        panes = self.tmux[self.chat_id]["panes"]
        if not idx in panes:
            return f"ERROR: {idx} does not exist!"
        pane = panes[idx]
        if pane.pane_dead == "1":
            del panes[idx]
            return f"{idx} is dead!"
        _output = pane.capture_pane(preserve_trailing=True, join_wrapped=True)
        x = int(pane.display_message('#{cursor_x}', get_text=True)[0])
        y = int(pane.display_message('#{cursor_y}', get_text=True)[0])
        output = ""
        count_y = 0
        for line in _output:
            if count_y == y:
                output += line[0:x] + "█"
                if len(line)-1 >= x+1:
                    output += line[x+1:]
                output += "\n"
            else:
                output += line + "\n"
            count_y += 1
        return "```text\n" + output + "\n```"

    def term_kill(self, idx: str) -> str:
        panes = self.tmux[self.chat_id]["panes"]
        if not idx in panes:
            return f"ERROR: {idx} does not exist!"
        if panes[idx].pane_dead == "1":
            del panes[idx]
            return f"{idx} already dead!"
        panes[idx].kill()
        del panes[idx]
        return f"Killed {idx}"

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
        yield "Running process...\n\n"
        proc = await asyncio.create_subprocess_exec(*cmd_args,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        cwd=self.sandbox_path, start_new_session=True)
        proc.stdin.write(self.script.encode())
        await proc.stdin.drain()
        proc.stdin.close()
        self.chat.watchdog(proc, self)
        async for data in proc.stdout:
            yield data.decode("UTF-8", errors="replace")
        if proc.returncode < 0:
            if self.timeout_reached:
                yield "\nProcess was terminated due to timeout limit!"
            elif self.terminated:
                yield "\nProcess was terminated by user!"
        else:
            yield f"\nProcess exited with code {proc.returncode}."
