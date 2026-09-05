# SPDX-License-Identifier: GPL-2.0
from spit_app.tools.run.run import Run, get_script, get_args
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Rename or move a file or directory (a symlink moves as a symlink). Never overwrites: the target path must not already exist.",
        "parameters": {
            "type": "object",
            "properties": {
                "old_path": {
                    "type": "string",
                    "description": "Current path of the file or directory"
                },
                "new_path": {
                    "type": "string",
                    "description": "New path. Must NOT already exist (rename never overwrites); its parent directory must exist"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Preview without renaming. Default: False"
                }
            },
            "required": ["old_path", "new_path"]
        }
    }
}

OUTPUT_TYPE_HINT = "text"
PATH_ARGS = ["old_path", "new_path"]

PROMPT = "Use this function to rename or move a file or directory; a symlink is moved as a symlink. It never overwrites: `new_path` must not already exist as a file, directory or dangling symlink, and its parent directory must already exist - move or delete a conflicting file first. File bytes, line endings and permissions are untouched; a directory moves whole and atomically on the same filesystem. `~` and `$VAR` are expanded in both paths. Validation with `dry_run=true` is identical to the real call and moves nothing."
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
    args = get_args(arguments, {"dry_run": False})
    script = args + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], 0)
    async for line in run.run():
        yield line
