import time
import json
from spit_app.tools.run.terminal import Terminal
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

# The values of the two enumerating arguments, in the order they are named in the
# error sentence. One list each, so a DESC value and the check cannot drift apart.
CAPTURE_MODES = ["text", "styled", "bytes"]
OUTPUT_FORMATS = ["text", "json"]

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
                },
                "command": {
                    "type": "array",
                    "description": "argv to start in a NEW session instead of the default bash, e.g. [\"python3\", \"main.py\"]. Applied only when the session is created."
                },
                "env": {
                    "type": "object",
                    "description": "Environment variables for the launched command, as {\"NAME\": \"value\"}. Applied only when the session is created."
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the launched command, as the pane's own filesystem sees it (~ and $VAR are NOT expanded). Applied only when the session is created."
                },
                "cols": {
                    "type": "integer",
                    "description": "Width in columns. Together with `rows` it is the size of a new session, and it resizes an existing one. Give both or neither."
                },
                "rows": {
                    "type": "integer",
                    "description": "Height in rows. See `cols`."
                },
                "capture": {
                    "type": "string",
                    "description": "What a screen capture holds: `text` (default, plain), `styled` (tmux's own ANSI attributes, so colours and borders can be asserted), `bytes` (styled with non-printables octal-escaped)."
                },
                "history": {
                    "type": "integer",
                    "description": "Pull this many lines of scrollback above the visible screen (capped at 500). Absent or 0: the visible screen only."
                },
                "diff": {
                    "type": "boolean",
                    "description": "Report only the lines that changed since your last plain-text read of this session, instead of the whole screen."
                },
                "wait_for": {
                    "type": "string",
                    "description": "A regular expression to wait for in the pane. It REPLACES `delay`: the call returns as soon as it matches."
                },
                "wait_stable": {
                    "type": "integer",
                    "description": "Milliseconds the screen must hold still before the call returns. It REPLACES `delay`."
                },
                "wait_timeout": {
                    "type": "number",
                    "description": "Seconds a `wait_for`/`wait_stable` wait may take before it gives up. Default: 15"
                },
                "send_bytes": {
                    "type": "array",
                    "description": "Raw byte strings sent after `input`, delivered exactly and with nothing interpreted: SGR mouse sequences, bracketed paste. A NUL byte is refused."
                },
                "format": {
                    "type": "string",
                    "description": "How the answer is shaped: `text` (default) or `json` - the screen rows plus cursor, geometry, pid and current command as data (for a dead pane: exit status, signal, death time)."
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
- A session that dies while you are not looking is not lost: the next capture of that name reports the pane's real final screen and `Exit status: N`, then the name is freed. Output that scrolls off a LIVE session is still gone, so redirect long-lived output to a file.
- Providing only the 'name' gives you a snapshot of the current terminal screen.
- The "Enter" key is never implied. Always use it explicitly. This is a real terminal.
- End all processes and close the session with ["exit", "Enter"] if you no longer need it.

Starting and sizing a session (a program under test, not just an interactive shell):
- `command` is the argv to run in a NEW session, `env` its extra environment, `cwd` its working directory as the pane's own filesystem sees it (`~` and `$VAR` are NOT expanded). All three apply only when the session is created: naming a session that already exists together with `command`, `env` or `cwd` is refused, because silently typing into the program that is already there is worse than an error.
- `cols` and `rows` set the size of a new session, and resize an existing live one. Give both or neither: a window has ONE size and half a geometry would be a guess. Geometry is per terminal, so a resize never disturbs another session of yours.
- `wait_for` (a regex) and `wait_stable` (milliseconds the screen must hold still) REPLACE the blind `delay`: the call returns when the thing you wait for has happened, or after `wait_timeout` seconds (default 15) with a `WARNING` saying so. Waiting is what makes a streaming program testable; `delay` is left for everything else.
- Aborting the chat (ctrl+escape) also ends an in-flight `wait_for`: the call returns with what the pane held at that moment and says it was aborted.

Reading a screen back:
- `capture` chooses what is captured: `text` (plain, the default), `styled` (tmux's own attributes - how a heading, a colour or a border is asserted), `bytes` (styled, non-printables octal-escaped). Stated plainly, because it is a tmux limit: every mode reads the pane's GRID, so a graphics sequence tmux does not model (Kitty/Sixel) is consumed by tmux and appears as its placeholder, never as its bytes.
- `history=N` pulls N lines of scrollback above the visible screen (capped at 500) instead of only the 24 rows.
- `diff` reports only the lines that changed since your last plain-text read of that session - cheaper to read than the whole screen on a long session. A first read says there is no baseline yet; styled and byte captures never move it.
- `format="json"` answers with data instead of prose: rows, `cursor_x`/`cursor_y`, `cols`/`rows`, `pane_pid`, `command`, and for a dead pane `exit_status`/`signal`/`dead_time`. Assert on those instead of parsing sentences.
- `send_bytes` injects raw bytes after `input`, unchanged - the way to drive a program's mouse handling or bracketed paste. A leading `-` and a literal ESC arrive as bytes; a NUL cannot cross an argv and is refused.

For one-shot, short-lived actions use dedicated file and command tools.
"""


SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)"}
}

def starts_a_program(arguments: dict) -> bool:
    return arguments.get("command") is not None or arguments.get("env") is not None \
        or arguments.get("cwd") is not None

def wait_was_asked(arguments: dict) -> bool:
    return arguments.get("wait_for") is not None or arguments.get("wait_stable") is not None

def send_bytes_error(arguments: dict) -> str|None:
    data = arguments.get("send_bytes")
    if data is None or not data:
        return None
    if not type(data) is list or not all(type(one) is str for one in data):
        return "ERROR: expected array of strings for argument 'send_bytes'!"
    # A NUL byte has no encoding in an argv: tmux would receive the argument cut
    # at it, so a caller that asked for b'\x00' would get a different byte stream
    # than the one it asserted on. Refuse rather than deliver a lie.
    if any("\x00" in one for one in data):
        return "ERROR: argument 'send_bytes' cannot contain a NUL byte!"
    return None

def check_arguments(arguments: dict) -> str|None:
    for key in ("cols", "rows", "history", "wait_stable"):
        if arguments.get(key) is not None and not type(arguments[key]) is int:
            return f"ERROR: expected integer for argument '{key}'!"
    if arguments.get("wait_timeout") is not None \
            and not type(arguments["wait_timeout"]) in (int, float):
        return "ERROR: expected a number for argument 'wait_timeout'!"
    for key, values in (("capture", CAPTURE_MODES), ("format", OUTPUT_FORMATS)):
        if arguments.get(key) is not None and arguments[key] not in values:
            return f"ERROR: expected {', '.join(values)} for argument '{key}'!"
    if arguments.get("env") is not None and not type(arguments["env"]) is dict:
        return "ERROR: expected object for argument 'env'!"
    if arguments.get("command") is not None and not type(arguments["command"]) in (list, str):
        return "ERROR: expected array for argument 'command'!"
    if (arguments.get("cols") is None) != (arguments.get("rows") is None):
        return "ERROR: 'cols' and 'rows' size a window together: give both or neither!"
    return send_bytes_error(arguments) or diff_error(arguments)

def diff_error(arguments: dict) -> str|None:
    # A `diff` compares the plain-text rows, so the two arguments that change WHAT
    # is captured have no meaning on it. Refusing beats answering with a text diff
    # to a caller that asked for a styled one -- "a value that was read and then
    # not used" is the defect family this file's suite exists on (test_tool_call).
    if arguments.get("diff"):
        for key in ("capture", "history"):
            if arguments.get(key) is not None:
                return f"ERROR: 'diff' compares plain text, so it takes no '{key}'!"
        if arguments.get("format") == "json":
            return "ERROR: argument 'diff' cannot be combined with format 'json'!"
    return None

def wait_note(kind: str, pattern, stable_ms, timeout) -> str:
    # Only the two kinds that are NEWS get a sentence: a matched wait and a stable
    # screen say what the caller asked for with the screen itself, and a dead pane
    # is reported by the capture. A silent timeout is the one outcome a caller must
    # not be able to read as success.
    if kind == "timeout":
        what = f"no match for `{pattern}`" if pattern \
            else f"the screen never held still for {stable_ms} ms"
        return f"\n\nWARNING: Wait timed out after {timeout} s: {what}."
    if kind == "aborted":
        return "\n\nWARNING: The user aborted this chat; the wait ended early."
    return ""

def call(app, arguments: dict, chat_id) -> str:
    load_user_settings(app, NAME, SETTINGS)
    terminal = Terminal(app, chat_id, SETTINGS["sandbox"]["value"])
    if not "name" in arguments or not arguments["name"]:
        return "ERROR: No session 'name' provided!"
    name = arguments["name"]
    # An abort cancels the wait that was running when the user pressed ctrl+escape,
    # never the next call: clear the flag before doing anything, or a stale abort
    # would make the next wait_for return "aborted" before it had waited at all.
    app.tmux.get(chat_id, {}).pop("abort", None)
    error = check_arguments(arguments)
    if error:
        return error
    cols, rows = arguments.get("cols"), arguments.get("rows")
    if not chat_id in app.tmux or not name in app.tmux[chat_id]["windows"]:
        error = terminal.term_new(name, command=arguments.get("command"),
                                 env=arguments.get("env"), cwd=arguments.get("cwd"),
                                 cols=cols, rows=rows)
        if error:
            return error
    elif starts_a_program(arguments):
        return (f"ERROR: session `{name}` already exists in this chat: `command`, `env` and "
                f"`cwd` apply only when a session is created. Send input to `{name}`, or "
                f"use another name.")
    elif cols is not None:
        error = terminal.resize(name, cols, rows)
        if error:
            return error
    if "input" in arguments and arguments["input"]:
        if not type(arguments["input"]) is list:
            return "ERROR: expected array for argument 'input'!"
        count = 0
        for inp in arguments["input"]:
            if not terminal.term_input(name, inp):
                if not count == len(arguments["input"])-1:
                    return f"{terminal.last_screen(name)}\n\nWARNING: unconsumed input: `{arguments['input'][count:]}`!"
                return f"{terminal.last_screen(name)}"
            count +=1
    data = arguments.get("send_bytes")
    if data:
        count = 0
        for one in data:
            if not terminal.send_bytes(name, one):
                return (f"{terminal.last_screen(name)}\n\nWARNING: session not live, "
                        f"{len(data)-count} of the `send_bytes` were not delivered!")
            count += 1
    note = ""
    if wait_was_asked(arguments):
        timeout = arguments.get("wait_timeout")
        timeout = 15.0 if timeout is None else timeout
        kind, _ = terminal.wait_for(name, pattern=arguments.get("wait_for"),
                                   stable_ms=arguments.get("wait_stable"),
                                   timeout=timeout)
        if kind == "bad-pattern":
            return f"ERROR: invalid regular expression for argument 'wait_for': `{arguments.get('wait_for')}`!"
        note = wait_note(kind, arguments.get("wait_for"),
                         arguments.get("wait_stable"), timeout)
    else:
        delay = 1
        if "delay" in arguments and arguments["delay"] is not None:
            if type(arguments["delay"]) is int:
                delay = arguments["delay"]
        time.sleep(delay)
    # `or "text"`, not the raw argument: term_screen()/screen_json() default the
    # mode in their own signature, and passing None through would reach them a mode
    # that is not "text" -- which turns off the cursor marker and the diff baseline.
    mode = arguments.get("capture") or "text"
    if arguments.get("format") == "json":
        return terminal.screen_json(name, mode=mode,
                                   history=arguments.get("history"),
                                   wait=arguments.get("wait_for"))
    if arguments.get("diff"):
        return f"{terminal.diff_screen(name)}{note}"
    return f"{terminal.term_screen(name, mode=mode,
                                 history=arguments.get('history'))}{note}"
