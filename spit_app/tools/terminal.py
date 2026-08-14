import time
from spit_app.tools.run.run import Run
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Control an interactive terminal session. Run interactive CLI and TUI applications.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Available actions: new, send_keys, screen, kill."
                },
                "id": {
                    "type": "string",
                    "description": "The id of the terminal session."
                },
                "keys": {
                    "type": "string",
                    "description": "The keys to send to the terminal session."
                },
                "enter": {
                    "type": "boolean",
                    "description": "Also send 'Enter' key after 'keys'. Default: True"
                },
                "literal": {
                    "type": "boolean",
                    "description": "Send all 'keys' as literals. Default: True"
                },
                "delay": {
                    "type": "integer",
                    "description": "Delay action screen by the given amount of seconds."
                }
            },
            "required": ["action"]
        }
    }
}

SANDBOX = True
PROMPT = """Use this function to control an interactive terminal session.

Descriptions of actions:
- new: Create a new terminal session. An 'id' will be returned for interacting with the session.
- send_keys: Send 'keys' to the terminal session. Examples: "This is text", "echo "Hello World!", ...
  If you want to send a key or key combinations like "C-c", "Up", "Left", ..., set parameter 'literal' to True.
- screen: Return the current state of the terminal screen with the cursor displayed as '█'.
- kill: Kill the terminal session with the 'id'.

Parameter 'id' is mandatory for actions 'send_keys', 'screen', 'kill'.
Parameter 'keys' is mandatory for action 'send_keys'.
Parameters 'enter' and 'literal' are optional for action 'send_keys'.
Parameter 'delay' is optional for action 'screen'.
"""


SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
}

def call(app, arguments: dict, chat_id) -> str:
    load_user_settings(app, NAME, SETTINGS)
    run = Run(app, chat_id, "", "", True, 0)
    if not "action" in arguments or not arguments["action"]:
        return "ERROR: No action!"
    action = arguments["action"]
    if action == "new":
        return run.term_new()
    if not "id" in arguments or not arguments["id"]:
        return f"ERROR: No id for action {arguments['action']}!"
    idx = arguments["id"]
    if action == "screen":
        if "delay" in arguments and arguments["delay"]:
            try:
                delay = int(arguments["delay"])
            except:
                delay = 1
            time.sleep(delay)
        return run.term_screen(idx)
    if action == "kill":
        return run.term_kill(idx)
    if action == "send_keys":
        if not "keys" in arguments or not arguments["keys"]:
            return "ERROR: argument keys missing!"
        keys = arguments["keys"]
        enter = arguments.get("enter", True)
        literal = arguments.get("literal", True)
        return run.term_send_keys(idx, keys, enter, literal)
    return f"ERROR: Action {action} is not understood!"
