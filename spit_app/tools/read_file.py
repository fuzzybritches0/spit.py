# SPDX-License-Identifier: GPL-2.0
from spit_app.tools.run.run import Run
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Read a text file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "An arbitrary directory path with a filename."
                }
            },
            "required": ["path"]
        }
    }
}

PROMPT = "Use this function to read the content of any type of text file."
SANDBOX = True

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)"}
}

SCRIPT = """
import sys

try:
    with open(path, "r") as f:
        print(f.read())
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
    script = f"path = \"{arguments['path']}\"\n" + EXEC["script"]
    run = Run(app.settings.path["sandbox"], chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
