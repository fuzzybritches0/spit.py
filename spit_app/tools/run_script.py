# SPDX-License-Identifier: GPL-2.0
import shutil
from pathlib import Path
from spit_app.tools.run.run import Run, wrap_script
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Run a script with any interpreter allowed.",
        "parameters": {
            "type": "object",
            "properties": {
                "interpreter": {
                    "type": "string",
                    "description": "The interpreter to use for running the script."
                },
                "script": {
                    "type": "string",
                    "description": "Script or a path to a script file."
                },
                "separate_stderr": {
                    "type": "boolean",
                    "description": ("Report stderr in a labelled section after the output "
                                    "rather than interleaved with it. Default: true; set "
                                    "false when the two streams form one dialogue whose "
                                    "order matters")
                }
            },
            "required": ["interpreter", "script"]
        }
    }
}

OUTPUT_TYPE_HINT = "text"

SANDBOX = True
MAX_SECONDS = 0
ALLOWED = "bash, python3, perl"
PROMPT = "Use this function to run a script with any interpreter on the allowed list and receive its output."
PROMPT_INST = "The following interpreters are allowed: [interpreters]. Timeout is set to [timeout]. When timeout is set to 0, there is no timeout limit."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)"},
    "timeout": { "value": MAX_SECONDS, "stype": "uinteger", "empty": False, "desc": "Timeout (0 = no timeout)"},
    "interpreters": {"value": ALLOWED, "stype": "text", "empty": False, "desc": "Allowed interpreters"}
}

STREAM_TOOL_RESPONSE = True

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    interpreter = arguments["interpreter"]
    if interpreter == "python" and not shutil.which("python"):
        interpreter = "python3"
    if not shutil.which(interpreter):
        yield f"ERROR: `{interpreter}` not found! Give user instructions to install!"
        return
    _script = Path(arguments["script"])
    if _script.is_file():
        script = _script.read_text(encoding='utf-8')
        yield f"Reading script from file `{_script}`.\n\n"
    else:
        script = arguments["script"]
    if not script.strip():
        yield "ERROR: script is empty!"
        return
    run = Run(app, chat_id, interpreter, wrap_script(script),
              SETTINGS["sandbox"]["value"], SETTINGS["timeout"]["value"],
              script_as_file=True)
    async for line in run.run():
        yield line
