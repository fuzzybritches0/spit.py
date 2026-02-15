# SPDX-License-Identifier: GPL-2.0
import os
import shutil
import asyncio
from time import time
from spit_app.tools.sandbox.sandbox import Sandbox
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

PROMPT = "Use this function to run Shell commands and receive their output."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}

def preflight_tests(command) -> str|None:
    ret = ""
    for cmd in ["bwrap", "bash"]:
        if not shutil.which(cmd):
            ret += f"ERROR: {cmd} not found! Give user instructions to install!\n"
    if ret:
        return ret
    return None

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    ret = preflight_tests(arguments["command"])
    if not shutil.which("bash"):
        yield "ERROR: bash not found! Give user instructions to install bash!"
    else:
        if ret:
            yield ret
        else:
            id = "." + str(time()) + chat_id
            with open(app.settings.path["sandbox"] / id, "w") as f:
                f.write(arguments["command"])
            sandbox = Sandbox(app.settings.path["sandbox"], ["bash", f"./{id}"])
            replace = f"./{id}: line 1: "
            try:
                async for line in sandbox.run_sandbox():
                    if line.startswith(replace):
                        linelen = len(replace)
                        yield line[linelen:]
                    else:
                        yield line
            except:
                raise
            finally:
                os.remove(app.settings.path["sandbox"] / id)
