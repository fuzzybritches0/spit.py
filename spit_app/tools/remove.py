# SPDX-License-Identifier: GPL-2.0
from spit_app.tools.run.run import Run
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Remove a file or directory recursively.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "An arbitrary path to a directory or file."
                }
            },
            "required": ["path"]
        }
    }
}

PROMPT = "Use this function to remove a file or directory recursively."
SANDBOX = True

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)"}
}

SCRIPT = """
import os
import sys
import shutil

if not os.path.exists(path):
    print(f"ERROR: {path} does not exist!")
    sys.exit(1)
if os.path.isfile(path):
    try:
        os.remove(path)
        print(f"{path} removed.")
    except Exception as exception:
        print(f"ERROR: {type(exception).__name__}: {exception}")
        sys.exit(1)
elif os.path.isdir(path):
    try:
        shutil.rmtree(path)
        print(f"{path} removed.")
    except Exception as exception:
        print(f"ERROR: {type(exception).__name__}: {exception}")
        sys.exit(1)
"""

EXEC = {
    "script": SCRIPT,
    "interpreter": "python3"
}

async def call_async_generator(app, arguments: dict, chat_id) -> str:
    load_user_settings(app, NAME, SETTINGS)
    args = f"path = \"{arguments['path']}\"\n"
    script = args + EXEC["script"]
    run = Run(app.settings.path["sandbox"], chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
