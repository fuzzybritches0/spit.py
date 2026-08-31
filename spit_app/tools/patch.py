# SPDX-License-Identifier: GPL-2.0
import json
from spit_app.tools.run.run import Run, get_script, get_args
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Apply a unified diff patch to a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File to patch"
                },
                "diff": {
                    "type": "string",
                    "description": "Diff content (unified format) or path to a diff file."
                },
                "reverse": {
                    "type": "boolean",
                    "description": "Reverse the patch (apply new -> old). Default: False"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Preview without applying. Default: False"
                }
            },
            "required": ["path", "diff"]
        }
    }
}

OUTPUT_TYPE_HINT = "text"

PROMPT = "Use this function to apply unified diff patches to a file. Write a hunk header before the body as `@@ -start[,count] +start[,count] @@`, or — since the counts are easy to get right only *after* the body is written — after the body using `^^` instead of `@@` (e.g. `^^ -1,4 +1,4 ^^`); it is moved to the start of the hunk and overrides any preceding `@@` header. A patch is either fully headed or fully headerless — never mix. Header line counts must match the hunk body exactly. Each hunk must match the file at its header position or in exactly one place (a headed hunk whose header position does not match is applied at the nearest match; a headerless hunk that matches in more than one place is rejected as ambiguous). If any hunk fails, the whole patch is rejected and the file is left unmodified."
PROMPT_INST = "Timeout is set to [timeout]. When timeout is set to 0, there is no timeout limit."
SANDBOX = True
MAX_SECONDS = 0

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)" },
    "timeout": { "value": MAX_SECONDS, "stype": "uinteger", "empty": False, "desc": "Timeout (0 = no timeout)"},
}

EXEC = {
    "script": get_script(__file__, "lines"),
    "interpreter": "python3"
}

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    path_arg = json.dumps(arguments["path"])
    diff_arg = json.dumps(arguments["diff"])
    args = get_args(arguments, {"reverse": False, "dry_run": False})
    script = args + EXEC["script"]
    run = Run(app, chat_id, EXEC["interpreter"], script,
              SETTINGS["sandbox"]["value"], SETTINGS["timeout"]["value"])
    async for line in run.run():
        yield line
