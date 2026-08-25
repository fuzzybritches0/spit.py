# SPDX-License-Identifier: GPL-2.0
NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
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

PROMPT = "To help the user manage their chat conversations, use this function to set a short description of what this chat conversation is about. Use this function throughout the chat conversion to keep the chat description up-to-date. Examples: 'Copy Python Objects', 'Paris Weather' ... then later in the conversation update to 'Paris, Vienna Weather, 'Creative Writing: Love Poem', 'Solving Quadratics' ... then later in the conversation update to 'Solving Quadratics: Factoring'"

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}
    
async def call(app, arguments: dict, chat_id: str) -> str|None:
    chat = app.query_one(f"#{chat_id}")
    chat.cs("desc", arguments["description"])
    chat.write_chat_history()
    app.query_one("#side-panel").update_option_prompt(chat_id)
    await app.maybe_reload("manage-chat")
    return "chat description set."
