# SPDX-License-Identifier: GPL-2.0
import json
from spit_app.tools.run.run import Run, get_script
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Save text in a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "An arbitrary directory path with a filename."
                },
                "content": {
                    "type": "string",
                    "description": "The content of the file."
                },
                "append": {
                    "type": "boolean",
                    "description": "Append to file instead of overwriting. Default: False"
                },
                "prepend_newline": {
                    "type": "boolean",
                    "description": "Prepend newline when appending to file. Default: True"
                },
                "create_dirs": {
                    "type": "boolean",
                    "description": "Create parent directories if they don't exist. Default: True"
                }
            },
            "required": ["path", "content"]
        }
    }
}

PROMPT = "Use this function to save any type of text content in a file. Any sub-directories that do not exist will be created for you."
SANDBOX = True

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)"}
}

EXEC = {
    "script": get_script(__file__),
    "interpreter": "python3"
}
    
async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    content = json.dumps(arguments["content"])
    args = f"""
path = "{arguments['path']}"
content = {content}
append = {arguments.get('append', False)}
prepend_newline = {arguments.get('prepend_newline', True)}
create_dirs = {arguments.get('create_dirs', True)}
"""
    script = args + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
