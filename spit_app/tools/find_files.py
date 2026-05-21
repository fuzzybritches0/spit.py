# SPDX-License-Identifier: GPL-2.0
from spit_app.tools.run.run import Run, get_script
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Find files matching patterns in directories.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to search in"
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match (e.g., '*.py', '*.txt'). Default: '*'"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Search subdirectories. Default: True"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results. Default: 100"
                }
            },
            "required": ["path"]
        }
    }
}

PROMPT = "Use this function to find files matching patterns in directories."
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
    script = f"""
path = "{arguments['path']}"
pattern = "{arguments.get('pattern', '*')}"
recursive = {arguments.get('recursive', True)}
max_results = {arguments.get('max_results', 100)}
""" + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
