# SPDX-License-Identifier: GPL-2.0
import json
from spit_app.tools.run.run import Run, get_script, get_args
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Compare two files and show differences.",
        "parameters": {
            "type": "object",
            "properties": {
                "file1": {
                    "type": "string",
                    "description": "First file path"
                },
                "file2": {
                    "type": "string",
                    "description": "Second file path"
                },
                "context": {
                    "type": "integer",
                    "description": "Context lines. Default: 3"
                },
                "output_format": {
                    "type": "string",
                    "description": "unified, context, side_by_side. Default: unified"
                }
            },
            "required": ["file1", "file2"]
        }
    }
}

OUTPUT_TYPE_HINT = "text"

PROMPT = "Use this function to compare two files and show differences. Supports unified, context, and side_by_side output formats."
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
    args = get_args(arguments, {"context": 3, "output_format": "unified"})
    script = args + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
