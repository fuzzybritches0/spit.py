# SPDX-License-Identifier: GPL-2.0
import httpx

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Get the current weather in a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA"
                }
            },
            "required": ["location"]
        }
    }
} 

PROMPT = "Use this function if the user asks you for the weather in some location."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}

async def call(app, arguments: dict, chat_id) -> dict:
    url = f"https://wttr.in/{arguments['location']}?format=j2"
    async with httpx.AsyncClient(timeout=15) as client:
        result = await client.get(url)
    return "```json\n" + result.text + "\n```"
