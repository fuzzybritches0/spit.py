# SPDX-License-Identifier: GPL-2.0

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
    location = arguments["path"].replace("..", "")
    if not location == arguments["path"]:
        return "ERROR: location not allowed!"
    location = location.lstrip("/")
    location = app.settings.path["sandbox"] / location
    with open(location, "r") as f:
        content = f.read()
    return arguments["path"] + ":\n\n```\n" + content + "\n```"
