# SPDX-License-Identifier: GPL-2.0
import os
import shutil
from time import time
from spit_app.tools.run.run import Run
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
                    "description": "The script to run."
                }
            },
            "required": ["interpreter", "script"]
        }
    }
}

SANDBOX = True
MAX_SECONDS = 0
ALLOWED = "bash, python3, perl"
PROMPT = "Use this function to run a script with any interpreter on the allowed list and receive its output."
PROMPT_INST = "The following interpreters are allowed: [allowed]. Timeout is set to [timeout]. When timeout is set to 0, there is no timeout limit."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)"},
    "timeout": { "value": MAX_SECONDS, "stype": "uinteger", "empty": False, "desc": "Timeout (0 = no timeout)"},
    "interpreters": {"value": ALLOWED, "stype": "text", "empty": False, "desc": "Allowed interpreters"}
}

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    if not shutil.which(arguments["interpreter"]):
        yield f"ERROR: {arguments['interpreter']} not found! Give user instructions to install!\n"
        return
    run = Run(app.settings.path["sandbox"], chat_id, arguments["interpreter"], arguments["script"],
              SETTINGS["sandbox"]["value"], SETTINGS["timeout"]["value"])
    async for line in run.run():
        yield line
