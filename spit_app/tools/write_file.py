# SPDX-License-Identifier: GPL-2.0
from pathlib import Path

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Save text in a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "An arbitrary directory path with a filename."
                },
                "content": {
                    "type": "string",
                    "description": "The content of the file."
                }
            },
            "required": ["path", "content"]
        }
    }
}

PROMPT = "Use this function to save any type of text content in a file. Any sub-directories that do not exist will be created for you."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}
    
def call(app, arguments: dict, chat_id) -> str:
    location = arguments["path"].replace("..", "")
    if not location == arguments["path"]:
        return "ERROR: location not allowed!"
    location = location.split("/")
    file = location[-1]
    location = "/".join(location[:-1])
    if not location:
        return "ERROR: location not valid!"
    location = app.settings.path["sandbox"] / location
    Path(location).mkdir(parents=True, exist_ok=True)
    try:
        with open(location / file, "w") as f:
            f.write(arguments["content"])
    except Exception as exception:
        return f"ERROR:\n\n{type(exception).__name__}: {exception}"
    return f"file {arguments['path']} saved."
