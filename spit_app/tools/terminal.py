import time
import json
from spit_app.tools.run.run import Run

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Control an interactive terminal session. Run interactive CLI and TUI applications.",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "The id of an existing terminal session."
                },
                "input": {
                    "type": "array",
                    "description": "Send any string of characters or keys to a terminal session."
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
The 'input' argument expects an array of strings of characters and/or keys that will be sent to the terminal session. The following keys are understood: Up, Down, Left, Right, Space, Tab, Delete, End, Enter, Escape, F1 ... F12, Home, Insert, PageDown, PageUp. To use key combinations, prefix them with 'C-' (Ctrl), 'S-' (Shift), 'M-' (Alt). Examples: ["echo \"Hello World!\"", "Enter"], ["vim test.txt", "Enter", "iHello test.txt file!", "Escape", ":wq", "Enter"]
If you omit 'id', a new session will be created. You can not pick an 'id'. Every screen capture is prepended with the its 'id'.
With at least the 'id' argument, a capture of the screen will be returned.
Quit all applications and end the session with ["exit", "Enter"] if you no longer need it!
"""


SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
}

def call(app, arguments: dict, chat_id) -> str:
    run = Run(app, chat_id, "", "", True, 0)
    if not "id" in arguments:
        idx = run.term_new()
    else:
        idx = arguments["id"]
    panes = {}
    if chat_id in app.tmux and "panes" in app.tmux[chat_id]:
        panes = app.tmux[chat_id]["panes"]
    if not type(idx) is int:
        return f"ERROR: Session '{idx}' invalid!"
    if not idx in panes or not panes[idx]:
        return f"ERROR: Session '{idx}' does not exist!"
    if "input" in arguments and arguments["input"]:
        if not type(arguments["input"]) is list:
            return "ERROR: expected array for argument 'input'!"
        for inp in arguments["input"]:
            ret = run.term_input(idx, inp)
            if ret:
                return ret
    delay = 1
    if "delay" in arguments and arguments["delay"]:
        if type(arguments["delay"]) is int:
                dealy = arguments["delay"]
    time.sleep(delay)
    return run.term_screen(idx)
