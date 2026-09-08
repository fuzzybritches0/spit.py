from spit_app.tool_call import load_user_settings
from spit_app.tools.run.terminal import live_window_names

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "List live terminal sessions."
    }
}

PROMPT = "Use this function to list all currently live terminal sessions. Call it before creating a new session to avoid accidentally interacting with a live session instead. Check if sessions are still alive before interacting with them - especially sessions you have not interacted with for a longer period of time. Sessions might also disappear due to system failure or user actions."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}

def call(app, arguments: dict, chat_id) -> str:
    load_user_settings(app, NAME, SETTINGS)
    live = live_window_names(app.tmux, chat_id)
    if live:
        return "# Currently active sessions:\n\n" + "".join(f"- `{window}`\n" for window in live)
    return "No active sessions found!"
