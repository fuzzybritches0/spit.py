# SPDX-License-Identifier: GPL-2.0
from pathlib import Path

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Read a text file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "An arbitrary directory path with a filename."
                }
            },
            "required": ["path"]
        }
    }
}

PROMPT = "Use this function to read the content of any type of text file."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}
    

def call(app, arguments: dict, chat_id) -> str:
    location = str(app.settings.path["sandbox"]) + "/" + arguments["path"]
    try:
        with open(location, "r") as f:
            content = f.read()
        return arguments["path"] + ":\n\n```\n" + content + "\n```"
    except Exception as exception:
        return f"ERROR:\n\n{type(exception).__name__}: {exception}"
