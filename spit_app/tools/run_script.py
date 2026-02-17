# SPDX-License-Identifier: GPL-2.0
import os
import shutil
import asyncio
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
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox"},
    "timeout": { "value": MAX_SECONDS, "stype": "uinteger", "empty": False, "desc": "Timeout (0 = no timeout)"},
    "interpreters": {"value": ALLOWED, "stype": "text", "empty": False, "desc": "Allowed interpreters"}
}

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    if not shutil.which(arguments["interpreter"]):
        yield f"ERROR: {arguments['interpreter']} not found! Give user instructions to install!\n"
        return
    id = "." + str(time()) + chat_id
    with open(app.settings.path["sandbox"] / id, "w") as f:
        f.write(arguments["script"])
    run = Run(app.settings.path["sandbox"], [arguments["interpreter"], f"./{id}"],
              SETTINGS["sandbox"]["value"], SETTINGS["timeout"]["value"])
    replace = f"./{id}"
    try:
        async for line in run.run():
            if replace in line:
                line = line.replace(replace, "./script")
            yield line
    except:
        raise
    finally:
        os.remove(app.settings.path["sandbox"] / id)
