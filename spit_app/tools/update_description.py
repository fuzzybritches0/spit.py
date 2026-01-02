# SPDX-License-Identifier: GPL-2.0

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
    
def call(app, arguments: dict, chat_id) -> dict:
    chat = app.query_one(f"#{chat_id}")
    desc = arguments["description"]
    chat.chat_desc = desc
    chat.write_chat_history
    app.query_one("#side-panel").replace_option_prompt(chat_id, f"\n{desc}\n{chat.chat_ctime}\n")
    return "chat description set."
