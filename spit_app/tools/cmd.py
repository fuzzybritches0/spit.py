# SPDX-License-Identifier: GPL-2.0
import asyncio
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Run a Shell command.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "A Shell command with optional arguments to run in the sandbox."
                }
            },
            "required": ["command"]
        }
    }
}

COMMANDS = "cat, cp, mv, ls, wc, head, tail, date, df, du, find, free, grep, id, ps, uptime, uname"
PROMPT = "Use this function to run Shell commands and receive their output."
PROMPT_INST= "The following commands are available: [commands]. Use './' to address the current working directory! Do not start path statements with '/'!"

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "commands": { "value": COMMANDS, "stype": "text", "desc": "Allowed commands" }
}

def sanitize_arguments(command) -> str|None:
    FORBIDDEN_CHARS = set(";|&`$()<>")
    if any(ch in command for ch in FORBIDDEN_CHARS):
        return f"ERROR: shell metacharacters not permitted!"
    arg0 = command.split(" ")[0]
    if not arg0 in COMMANDS:
        return f"ERROR: permission denied for: {arg0}!"
    elif ".." in command:
        return f"ERROR: {command} containing '..' not permitted!"
    elif "\\" in command:
        return f"ERROR: {command} containing '\\' not permitted!"
    args = command.split(" ")
    for arg in args:
        if arg.startswith("/") or arg.startswith('"/') or arg.startswith("'/"):
            return f"ERROR: '{arg}' path statement starting with '/' not permitted!"
        elif arg.startswith("-") and "/" in arg and not "=" in arg:
            return f"ERROR: unable to sanitize {arg}! Separate arguments from path statements!"
        elif "=/" in arg or '="/' in arg or "='/" in arg:
            return f"ERROR: {arg} path statement starting with '/' not permitted!"
    return None

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    san = sanitize_arguments(arguments["command"])
    if san:
        yield san
    else:
        yield "```\n"
        command = arguments["command"].split(" ")
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE,
                                                        stderr=asyncio.subprocess.STDOUT,
                                                        cwd=app.settings.path["sandbox"])
            while True:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    break
                yield line_bytes.decode("UTF-8", errors="replace")
        except Exception as exception:
            yield f"{type(exception).__name__}: {exception}"
        finally:
            if proc and proc.returncode is None:
                proc.terminate()
                await proc.wait()
        yield "\n```"
