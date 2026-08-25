from spit_app.tool_call import load_user_settings

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

def pane_active(app, chat_id: str, name: str) -> bool:
    app.tmux[chat_id]["session"].refresh()
    if app.tmux[chat_id]["windows"][name] in app.tmux[chat_id]["session"].windows:
        return True
    else:
        del app.tmux[chat_id]["windows"][name]
        return False

def call(app, arguments: dict, chat_id) -> str:
    load_user_settings(app, NAME, SETTINGS)
    ret = ""
    if chat_id in app.tmux and "windows" in app.tmux[chat_id]:
        for window in app.tmux[chat_id]["windows"].keys():
            if pane_active(app, chat_id, window):
                ret += f"- `{window}`\n"
        if ret:
            return "# Currently active sessions:\n\n" + ret
    return "No active sessions found!"
