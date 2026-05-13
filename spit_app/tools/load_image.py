# SPDX-License-Identifier: GPL-2.0
import asyncio
from spit_app.chat.multimodal import load_image_base64, image_url

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Load an image file so you can look at it.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the image file."
                }
            },
            "required": ["file_path"]
        }
    }
} 

PROMPT = "Use this function if you need to look at an image."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}

async def call(app, arguments: dict, chat_id) -> str|None:
    sandbox_home = app.query_one("#main").query_one(f"#{chat_id}").csettings["sandbox"]["value"]
    sandbox_path = app.settings.path["sandbox"] / sandbox_home
    file_path = arguments["file_path"]
    if file_path.startswith("/home"):
        file_path = str(sandbox_path) + "/" + "/".join(file_path.split("/")[3:])
    elif file_path.startswith("~"):
        file_path = str(sandbox_path) + "/" + file_path[1:]
    else:
        return "ERROR: 'file_path' must be absolute!"
    image = await asyncio.to_thread(load_image_base64, file_path)
    messages = app.query_one("#main").query_one(f"#{chat_id}").messages
    messages[-1]["content"].append(image_url(image))
    return f"Loading image: {arguments['file_path']}"

