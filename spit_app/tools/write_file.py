# SPDX-License-Identifier: GPL-2.0

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
    file = location.split("/")[-1]
    location = location.split("/")[:-1]
    if location:
        location = "/".join(location)
        location = app.settings.path["sandbox"] / location.lstrip("/")
        location.mkdir(parents=True, exist_ok=True)
        file = location / file
    else:
        file = app.settings.path["sandbox"] / file
    with open(file, "w") as f:
        f.write(arguments["content"])
    return f"file {arguments['path']} saved."
