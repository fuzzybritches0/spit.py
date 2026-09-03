# SPDX-License-Identifier: GPL-2.0
import json
from spit_app.tools.run.run import Run, get_script, get_args
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Find and replace text in a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path"
                },
                "find": {
                    "type": "string",
                    "description": "Text or regex pattern to find"
                },
                "replace": {
                    "type": "string",
                    "description": "Replacement text"
                },
                "use_regex": {
                    "type": "boolean",
                    "description": "Treat find as regex. Default: False"
                },
                "max_replacements": {
                    "type": "integer",
                    "description": "Limit replacements. Default: 0 (all)"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Don't change file. Only show count of replacements. Default: False"
                }
            },
            "required": ["path", "find", "replace"]
        }
    }
}

PATH_ARGS = ["path"]

PROMPT = "Use this function to find and replace text in a file."
PROMPT_INST = "Timeout is set to [timeout]. When timeout is set to 0, there is no timeout limit."
SANDBOX = True
MAX_SECONDS = 0

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)" },
    "timeout": { "value": MAX_SECONDS, "stype": "uinteger", "empty": False, "desc": "Timeout (0 = no timeout)"},
}

EXEC = {
    "script": get_script(__file__),
    "interpreter": "python3"
}

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    args = get_args(arguments, {"use_regex": False, "max_replacements": 0, "dry_run": False})
    script = args + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], SETTINGS["timeout"]["value"])
    async for line in run.run():
        yield line
