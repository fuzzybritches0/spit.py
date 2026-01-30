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
                "location": {
                    "type": "string",
                    "description": "An arbitrary directory path with a filename."
                },
                "content": {
                    "type": "string",
                    "description": "The content of the file."
                }
            },
            "required": ["location", "content"]
        }
    }
}

PROMPT = "Use this function to save any type of text content in a file. Any sub-directories that do not exist will be created for you."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}
    
def call(app, arguments: dict, chat_id) -> str:
    location = arguments["location"].replace("..", "")
    if not location == arguments["location"]:
        return "ERROR: location not allowed!"
    location = location.split("/")
    file = location[-1]
    if not file:
        return "ERROR: no file name in location!"
    location = "/".join(location[:-1])
    if not location:
        return "ERROR: location not valid!"
    location = str(app.settings.path["sandbox"]) + "/" + location
    Path(location).mkdir(parents=True, exist_ok=True)
    with open(location + "/" + file, "w") as f:
        f.write(arguments["content"])
    return "file saved."
