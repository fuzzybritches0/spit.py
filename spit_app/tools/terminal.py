import time
import json
from spit_app.tools.run.run import Run
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Control interactive terminal sessions. Run interactive CLI and TUI applications.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The terminal session name."
                },
                "input": {
                    "type": "array",
                    "description": "Send any string-of-characters or keys to a terminal session."
                },
                "delay": {
                    "type": "integer",
                    "description": "Delay before capturing the terminal screen (seconds). Default: 1"
                }
            }
        }
    }
}

SANDBOX = True
PROMPT = """
The 'input' argument expects an array of string-of-characters and/or keys that will be send to the terminal session. The following keys are understood: Up, Down, Left, Right, Space, Tab, Delete, End, Enter, Escape/Esc, F1 ... F12, Home, Insert, PageDown/PgDn, PageUp/PgUp. To use key combinations, prefix them with 'C-' (Ctrl), 'S-' (Shift), 'M-' (Alt). Examples: ["echo \"Hello World!\"", "Enter"], ["vim test.txt", "Enter"], ["iHello test.txt file!", "Escape", ":wq", "Enter"]
Every screen capture is prepended with its 'name' so you know which output belongs to which session.
Only providing the 'name', a capture of the screen will be returned.
Quit all applications and end all sessions with ["exit", "Enter"] if you no longer need them!
"""


SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)"}
}

def call(app, arguments: dict, chat_id) -> str:
    load_user_settings(app, NAME, SETTINGS)
    run = Run(app, chat_id, "", "", SETTINGS["sandbox"]["value"], 0)
    if not "name" in arguments or not arguments["name"]:
        return "ERROR: No session 'name' provided!"
    name = arguments["name"]
    if not chat_id in app.tmux or not name in app.tmux[chat_id]["windows"]:
        run.term_new(name)
    windows = app.tmux[chat_id]["windows"]
    if "input" in arguments and arguments["input"]:
        if not type(arguments["input"]) is list:
            return "ERROR: expected array for argument 'input'!"
        count = 0
        for inp in arguments["input"]:
            if not run.term_input(name, inp):
                if not count == len(arguments["input"])-1:
                    return f"{run.output}\n\nWARNING: unconsumed input: `{arguments['input'][count:]}`!"
                return f"{run.output}"
            count +=1
    delay = 1
    if "delay" in arguments and arguments["delay"]:
        if type(arguments["delay"]) is int:
                dealy = arguments["delay"]
    time.sleep(delay)
    return run.term_screen(name)
