import time
import json
from spit_app.tools.run.run import Run
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Control persistent interactive terminal sessions with a 24x80 characters window.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The terminal session name."
                },
                "input": {
                    "type": "array",
                    "description": "An array of string-of-characters and/or key names to send to the terminal."
                },
                "delay": {
                    "type": "integer",
                    "description": "Seconds to wait before capturing the screen after sending input. Default: 1"
                }
            },
            "required": ["name"]
        }
    }
}

OUTPUT_TYPE_HINT = "text"

SANDBOX = True
PROMPT = """
The 'input' argument expects an array of string-of-characters and/or keys that will be send to the terminal session.

Supported keys: Up, Down, Left, Right, Space, Tab, Delete, End, Enter, Escape/Esc, F1-F12, Home, Insert, PageDown/PgDn, PageUp/PgUp. For key combinations use prefixes: 'C-' (Ctrl), 'S-' (Shift), 'M-' (Alt).

Examples:
- Use an editor: ["vim test.txt", "Enter", "iHello test.txt file!", "Escape", ":wq", "Enter"]
- Start a background process: ["npm run dev > dev.log 2>&1 &", "Enter"]
- Send a signal ["C-c"]

Key limitations to keep in mind:
- The terminal is 24x80 characters with no scroll-back. Each screen capture shows only the 24 lines.
- When a session dies while not interacting with it, no output can be recovered. Use redirects.
- Providing only the 'name' gives you a snapshot of the current terminal screen.
- The "Enter" key is never implied. Always use it explicitly. This is a real terminal.
- End all processes and close the session with ["exit", "Enter"] if you no longer need it.

For one-shot, short-lived actions use dedicated file and command tools.
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
