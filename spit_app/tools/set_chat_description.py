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

PROMPT = "To help the user manage their chat conversations, use this function to set a short description of what this chat conversation is about.\nAfter every user turn, determine what the topic of this conversation is. Should the topic of the conversation not be clear right away, postpone using this function until you know what this conversation is about.\nShould the topic, in the course of the conversation, change or touch a more broader field, use the function again to add to or broaden the description. The description should not be longer than 7 words. Avoid using general descriptions like 'Chat Conversation', 'Greetings', ...\nExamples to consider: 'Copy Python Objects', 'Paris, Vienna Weather', 'Creative Writing: Love Poem', 'Solving Quadratics: Factoring'"

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}
    
async def call(app, arguments: dict, chat_id) -> str:
    chat = app.query_one(f"#{chat_id}")
    chat.chat_desc = arguments["description"]
    chat.write_chat_history()
    app.query_one("#side-panel").update_option_prompt(chat_id)
    await app.maybe_remove("manage-chats")
    return "chat description set."
