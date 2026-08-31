# SPDX-License-Identifier: GPL-2.0
from spit_app.tools.run.run import Run, get_script, get_args
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Insert line(s) at a specific position in a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path"
                },
                "content": {
                    "type": "string",
                    "description": "Content to insert (may span multiple lines)"
                },
                "line_number": {
                    "type": "integer",
                    "description": "Line to insert before (1 = beginning). Default: 1"
                },
                "after_line": {
                    "type": "integer",
                    "description": "Insert after this line number (0 = beginning). Mutually exclusive with line_number. Default: None"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Preview without applying. Default: False"
                }
            },
            "required": ["path", "content"]
        }
    }
}

OUTPUT_TYPE_HINT = "text"

PROMPT = "Use this function to insert line(s) at a specific position in a file. Use `line_number` to insert before a line, or `after_line` to insert after a line. They are mutually exclusive. To append at the end, use line_number=n+1 or after_line=n."
SANDBOX = True

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)" }
}

EXEC = {
    "script": get_script(__file__, "lines"),
    "interpreter": "python3"
}

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    args = get_args(arguments, {"line_number": 1, "after_line": None, "dry_run": False})
    script = args + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
