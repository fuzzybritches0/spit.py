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

PROMPT = "Use this function to apply unified diff patches to a file. Write each hunk as a standard unified diff hunk: a header `@@ -start[,count] +start[,count] @@` followed by its body lines (` ` context, `-` removed, `+` added). The counts in the header are IGNORED — only the two start line numbers are used, so you never need to count the hunk's lines. A hunk applies wherever it can be placed unambiguously: if its body matches the file in exactly one place it is applied there, whatever the header says; if it matches several places, the header's start line picks the nearest one, and a tie between two equally near places is refused as ambiguous (add context lines or point the header at the line you mean). Hunks may mix headed and headerless ones, but a headerless hunk has nothing to break a tie, so its body must match in exactly one place; a hunk that only inserts lines needs a header to say where. A blank line inside a hunk is written as a single space (` `) for context, or as `+`/`-` when it is added or removed; a truly empty line separates hunks. Hunks must cover different parts of the file: two hunks claiming the same line are rejected. Every hunk is matched against the file as it is before the patch, so one hunk's change never affects where another hunk is placed. If any hunk fails, the whole patch is rejected and the file is left unmodified."
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
