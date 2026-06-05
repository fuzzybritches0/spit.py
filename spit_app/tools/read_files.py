# SPDX-License-Identifier: GPL-2.0
import json
from spit_app.tools.run.run import Run, get_script
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Read one or more text files.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": ["string", "array"],
                    "description": "A file path or list of file paths"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding. Default: 'utf-8'"
                }
            },
            "required": ["path"]
        }
    }
}

PROMPT = "Use this function to read the content of one or more text files."
SANDBOX = True

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)" }
}

EXEC = {
    "script": get_script(__file__),
    "interpreter": "python3"
}

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    encoding = arguments.get('encoding', 'utf-8')
    path = arguments["path"]
    if path is type(str) and not path.strip().startswith("["):
            path = '"' + path + '"'
    script = f"""
paths = {path}
encoding = "{encoding}"
""" + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
