# SPDX-License-Identifier: GPL-2.0
import os
import shlex
import shutil
import asyncio
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Run a Shell command.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute."
                }
            },
            "required": ["command"]
        }
    }
}

PROMPT = "Use this function to run Shell commands and receive their output. You can only write files in the current directory."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}

def bwrap_args(app) -> list:
    nobind = ["dev", "proc", "boot", "home", "tmp"]
    args = ["bwrap"]
    for d in os.listdir("/"):
        if not d in nobind:
            args += ["--bind", f"/{d}", f"/{d}"]
    args += ["--chdir", "/home/user"]
    args += ["--bind", app.settings.path['sandbox'], "/home/user"]
    args += ["--share-net", "--unshare-all", "--proc", "/proc",
             "--dev", "/dev", "--tmpfs", "/tmp", "--new-session"]
    return args

def preflight_tests(command) -> str|None:
    FORBIDDEN_CHARS = set(";|&`$()<>")
    if any(ch in command for ch in FORBIDDEN_CHARS):
        return f"ERROR: shell metacharacters not permitted!"
    cmd = command.split(" ", 1)
    if not shutil.which(cmd[0]):
        return f"ERROR: {cmd[0]} not in $PATH!"
    if not shutil.which("bwrap"):
        return "ERROR: bubblewrap not found! Please install with `apt install bubblewrap`!"
    return None


async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    ret = preflight_tests(arguments["command"])
    if ret:
        yield ret
    else:
        cmd_args = bwrap_args(app) + shlex.split(arguments["command"])
        yield "```\n"
        proc = await asyncio.create_subprocess_exec(*cmd_args, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.STDOUT,
                                                cwd=app.settings.path["sandbox"])
        while True:
            line_bytes = await proc.stdout.readline()
            if not line_bytes:
                break
            yield line_bytes.decode("UTF-8", errors="replace")
        if proc and proc.returncode is None:
            proc.terminate()
            await proc.wait()
        yield "\n```"
