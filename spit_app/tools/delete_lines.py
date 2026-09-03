# SPDX-License-Identifier: GPL-2.0
from spit_app.tools.run.run import Run, get_script, get_args
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Delete lines from a file by line number range and/or by regex pattern.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path"
                },
                "start_line": {
                    "type": "integer",
                    "description": "First line to delete (1-based, inclusive). Alone it deletes just that line. Omit to delete by pattern only. Default: None"
                },
                "end_line": {
                    "type": "integer",
                    "description": "Last line to delete (1-based, inclusive). Defaults to start_line. Requires start_line. Default: None"
                },
                "pattern": {
                    "type": "string",
                    "description": "Regex deleted from every line it matches (matched per line, searched anywhere unless anchored with ^ or $). With a line range only matching lines inside the range are deleted. Default: None"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Preview without deleting. Default: False"
                }
            },
            "required": ["path"]
        }
    }
}

OUTPUT_TYPE_HINT = "text"
PATH_ARGS = ["path"]

PROMPT = "Use this function to delete lines from a file by line number range and/or by regex pattern. Lines are 1-based and `end_line` is inclusive and defaults to `start_line`, so `start_line=5` alone deletes only line 5. With `pattern` alone every matching line in the file is deleted; with `pattern` plus a range only the matching lines inside that range are deleted. Read the file first with `read_files(show_line_numbers=true)` to get reliable line numbers. A pattern that matches nothing is not an error: nothing changes. Preview anything uncertain with `dry_run=true` — the preview is a unified diff you can hand to the `patch` tool."
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
    args = get_args(arguments, {"start_line": None, "end_line": None,
                                "pattern": None, "dry_run": False})
    script = args + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
