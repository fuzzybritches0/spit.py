# SPDX-License-Identifier: GPL-2.0
from datetime import datetime

desc = {
    "type": "function",
    "function": {
        "name": "update_description",
        "description": "Update the description of the current chat.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A short description of what this chat is about."
                }
            },
            "required": ["description"]
        }
    }
} 
    
async def call_async(app, arguments: dict, chat_id) -> str:
    chat = app.query_one(f"#{chat_id}")
    desc = arguments["description"]
    ctime = datetime.fromtimestamp(chat.chat_ctime)
    chat.chat_desc = desc
    chat.write_chat_history
    app.query_one("#side-panel").replace_option_prompt(chat_id, f"\n{desc}\n{ctime}\n")
    try:
        await app.query_one("#main").query_one("#manage-chats").remove()
    except:
        pass
    return "chat description set."
