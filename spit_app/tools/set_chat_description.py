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

PROMPT = "To help the user manage their chat conversations, use this function to set a short description of what this chat conversation is about. This is the function you always call first, before any other tool call, but after you have determined the topic of the conversation. Update the description over the course of the conversation as needed. Examples to consider: 'Copy Python Objects', 'Paris, Vienna Weather', 'Creative Writing: Love Poem', 'Solving Quadratics: Factoring'"

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}
    
async def call(app, arguments: dict, chat_id) -> str:
    chat = app.query_one(f"#{chat_id}")
    chat.chat_desc = arguments["description"]
    chat.write_chat_history()
    app.query_one("#side-panel").update_option_prompt(chat_id)
    await app.maybe_remove("manage-chat")
    return "chat description set."
