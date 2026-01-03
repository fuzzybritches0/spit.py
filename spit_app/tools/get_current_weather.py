# SPDX-License-Identifier: GPL-2.0

desc = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get the current weather in a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA"
                },
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
            },
            "required": ["location"]
        }
    }
} 
    
def call_sync(app, arguments: dict, chat_id) -> dict:
    return '{"unit":"celsius","temperature":3}'
