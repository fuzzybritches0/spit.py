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
                "location": {
                    "type": "string",
                    "description": "An arbitrary directory path with a filename."
                }
            },
            "required": ["location"]
        }
    }
}

PROMPT = "Use this function to read the content of any type of text file."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}
    

def call(app, arguments: dict, chat_id) -> str:
    location = str(app.settings.sandbox) + "/" + arguments["location"]
    try:
        with open(location, "r") as f:
            content = f.read()
        return arguments["location"] + ":\n\n```" + content + "```"
    except:
        return "ERROR: could not read file!"
