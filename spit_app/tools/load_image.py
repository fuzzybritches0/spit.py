# SPDX-License-Identifier: GPL-2.0
import asyncio
from spit_app.chat.multimodal import load_image_base64, image_url

NAME = __file__.split("/")[-1][:-3]

REQUIRES_MULTIMODAL_IMAGE = True

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Load an image file so you can look at it.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The absolute path to a local image file like '/home/user/image.jpg', or '~/image.jpg', or a 'http://' or 'https://' URL."
                }
            },
            "required": ["url"]
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
    url = arguments["url"]
    if url.startswith("/home"):
        url = str(sandbox_path) + "/" + "/".join(url.split("/")[3:])
    elif url.startswith("~"):
        url = str(sandbox_path) + "/" + url[1:]
    elif not url.startswith("http://") and not url.startswith("https://"):
        return "ERROR: 'url' must be an absolute local path or start with 'http://' or 'https://'!"
    image = await asyncio.to_thread(load_image_base64, url)
    messages = app.query_one("#main").query_one(f"#{chat_id}").messages
    messages[-1]["content"].append(image_url(image))
    return f"Loading image: {arguments['url']}"
