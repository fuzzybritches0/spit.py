# SPDX-License-Identifier: GPL-2.0
import shutil
from spit_app.tools.run.run import Run
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Run a Shell command.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute."
                }
            },
            "required": ["command"]
        }
    }
}

SANDBOX = True
MAX_SECONDS = 0
PROMPT = "Use this function to run Shell commands and receive their output."
PROMPT_INST = "Timeout is set to [timeout]. When timeout is set to 0, there is no timeout limit."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)"},
    "timeout": { "value": MAX_SECONDS, "stype": "uinteger", "empty": False, "desc": "Timeout (0 = no timeout)"},
}

STREAM_TOOL_RESPONSE = True

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    if not shutil.which("bash"):
        yield f"ERROR: `bash` not found! Give user instructions to install!\n"
        return
    run = Run(app, chat_id, "bash", arguments["command"] +
              "; EXIT_CODE=${?}; declare > ~/.sandbox_env; export -p >> ~/.sandbox_env; exit ${EXIT_CODE}",
              SETTINGS["sandbox"]["value"], SETTINGS["timeout"]["value"])
    yield "~~~~\n"
    async for line in run.run():
        yield line
    yield "\n~~~~"
