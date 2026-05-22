# SPDX-License-Identifier: GPL-2.0
import json
from spit_app.tools.run.run import Run, get_script
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Get detailed metadata for a single file or directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File or directory path"
                },
                "format": {
                    "type": "string",
                    "description": "Output format: 'text', 'json'. Default: 'text'"
                }
            },
            "required": ["path"]
        }
    }
}

PROMPT = "Use this function to get detailed metadata for a single file or directory. Returns size, permissions, modification time, file type, owner, group, and more."
SANDBOX = True

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)" }
}

EXEC = {
    "script": get_script(__file__, "file"),
    "interpreter": "python3"
}

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    script = f"""
path = "{arguments['path']}"
format = "{arguments.get('format', 'text')}"
""" + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
