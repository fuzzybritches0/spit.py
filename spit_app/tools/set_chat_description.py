# SPDX-License-Identifier: GPL-2.0
from datetime import datetime

name = __file__.split("/")[-1][:-3]

desc = {
    "type": "function",
    "function": {
        "name": name,
        "description": "Set the description of the current chat conversation.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A short description of what this chat conversation is about."
                }
            },
            "required": ["description"]
        }
    }
}

prompt = """
To help the user manage their chat conversations more easily, use this function to set a short description of what this chat conversation is about.
After every user turn, consider if you can determine the topic of the chat conversation, and set the description accordingly.
Should the topic, in the course of the conversation, change or touch a more broader field, use the function again to update or broaden the description. The description should not be longer than 7 words.
Examples: "Copy Python Objects", "Paris, Vienna Weather", "Creative Writing: Love Poem", "Solving Quadratics by Factoring"
"""

settings = {
    "display": { "value": False, "type": "Boolean" },
    "prompt": { "value": prompt, "type": "String" }
}
    
async def call(app, arguments: dict, chat_id) -> str:
    chat = app.query_one(f"#{chat_id}")
    ctime = datetime.fromtimestamp(chat.chat_ctime)
    chat.chat_desc = arguments["description"]
    chat.write_chat_history()
    app.query_one("#side-panel").update_option_prompt(chat_id)
    await app.maybe_remove("manage-chats")
    return "chat description set."
