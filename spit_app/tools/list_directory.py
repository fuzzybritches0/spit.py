# SPDX-License-Identifier: GPL-2.0
from spit_app.tools.run.run import Run, get_script
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Get directory contents with metadata including file sizes, owner/group, type (file/dir/link/block/char/fifo/socket), and modification times. Useful for exploring file systems and identifying special files like device nodes and symlinks.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Include subdirectories. Default: False"
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Include hidden files (starting with .). Default: False"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Only show 'max_results' results. Min: 1, Max: 10000, Default = 100"
                }
            },
            "required": ["path"]
        }
    }
}

PROMPT = "Use this function to get directory contents with metadata including owner/group, file type, size, and modification times."
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
recursive = {arguments.get('recursive', False)}
show_hidden = {arguments.get('show_hidden', False)}
max_results = {arguments.get('max_results', 100)}
""" + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
