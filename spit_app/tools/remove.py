# SPDX-License-Identifier: GPL-2.0
import os
import shutil
from pathlib import Path

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Remove a file or directory recursively.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "An arbitrary path to a directory or file."
                }
            },
            "required": ["path"]
        }
    }
}

PROMPT = "Use this function to remove a file or directory recursively."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}
    
def call(app, arguments: dict, chat_id) -> str:
    location = arguments["path"]
    if ".." in location:
        return "ERROR: location not allowed!"
    location = app.settings.path["sandbox"] / location
    if not os.path.exists(location):
        return f"ERROR: {location} does not exist!"
    if os.path.isfile(location):
        try:
            os.remove(location)
            return f"{arguments['path']} removed."
        except Exception as exception:
            return f"ERROR:\n\n{type(exception).__name__}: {exception}"
    if os.path.isdir(location):
        try:
            shutil.rmtree(location)
            return f"{arguments['path']} removed."
        except Exception as exception:
            return f"ERROR:\n\n{type(exception).__name__}: {exception}"
