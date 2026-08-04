# SPDX-License-Identifier: GPL-2.0
import json
from spit_app.tools.run.run import Run, get_script
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Find and replace text in files (with preview).",
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
                "preview": {
                    "type": "boolean",
                    "description": "Show matches before replacing. Default: True"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Only show preview. Implies preview=True. Default=False"
                }
            },
            "required": ["path", "find", "replace"]
        }
    }
}

PROMPT = "Use this function to find and replace text in files (with preview)."
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
    find = json.dumps(arguments["find"])
    replace = json.dumps(arguments["replace"])
    args = f"""
path = "{arguments['path']}"
find = {find}
replace = {replace}
use_regex = {arguments.get('use_regex', False)}
preview = {arguments.get('preview', True)}
dry_run = {arguments.get('dry_run', False)}
max_replacements = {arguments.get('max_replacements', 0)}
"""
    script = args + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
