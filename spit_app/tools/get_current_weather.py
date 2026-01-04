# SPDX-License-Identifier: GPL-2.0

name = __file__.split("/")[-1][:-3]

desc = {
    "type": "function",
    "function": {
        "name": name,
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

prompt = """
Use this function if the user asks you for the weather in some location.
"""

settings = {
    "display": { "value": False, "type": "Boolean" },
    "prompt": { "value": prompt, "type": "String" }
}

def call(app, arguments: dict, chat_id) -> dict:
    return '{"unit":"celsius","temperature":3}'
