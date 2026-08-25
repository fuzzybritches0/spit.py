# SPDX-License-Identifier: GPL-2.0
import json
from spit_app.tools.run.run import Run, get_script
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Search file contents for regex patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory to search"
                },
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File name filter (e.g., '*.py'). Default: '*'"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Search subdirectories. Default: True"
                },
                "context": {
                    "type": "integer",
                    "description": "Lines before/after match. Default: 0"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results. Default: 100"
                }
            },
            "required": ["path", "pattern"]
        }
    }
}

OUTPUT_TYPE_HINT = "text"

PROMPT = "Use this function to search file contents for regex patterns."
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
    pattern = json.dumps(arguments["pattern"])
    args = f"""
path = "{arguments['path']}"
pattern = {pattern}
file_pattern = "{arguments.get('file_pattern', '*')}"
recursive = {arguments.get('recursive', True)}
context = {arguments.get('context', 0)}
max_results = {arguments.get('max_results', 100)}
"""
    script = args + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], SETTINGS["timeout"]["value"])
    async for line in run.run():
        yield line
