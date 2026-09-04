# SPDX-License-Identifier: GPL-2.0
import shutil
from spit_app.tools.run.run import Run, wrap_script
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
                    "description": "The command to execute."
                },
                "separate_stderr": {
                    "type": "boolean",
                    "description": ("Report stderr in a labelled section after the output "
                                    "rather than interleaved with it. Default: true; set "
                                    "false when the two streams form one dialogue whose "
                                    "order matters")
                }
            },
            "required": ["command"]
        }
    }
}

OUTPUT_TYPE_HINT = "text"

SANDBOX = True
MAX_SECONDS = 0
# work.py concatenates PROMPT and PROMPT_INST with no separator, hence the
# trailing newline: without it the timeout sentence runs into this one.
PROMPT = ("Use this function to run Shell commands and receive their output. "
          "Nothing you background outlives the call: the command's process group is "
          "killed when the command ends, and inside the sandbox `--die-with-parent` "
          "tears the whole thing down. Use the `terminal` tool for a server, a tail, "
          "a REPL -- anything meant to keep running; `setsid cmd &` is the escape "
          "hatch, since it leaves the group and survives. stderr is reported in a "
          "`~~~~ stderr ~~~~` block after the output, and only when there is stderr; "
          "set `separate_stderr=false` to interleave the two streams when their "
          "relative order is the point. `export` and `cd` carry over to the next "
          "call; `~` and `$VAR` are expanded in the arguments that hold paths.\n")
PROMPT_INST = "Timeout is set to [timeout]. When timeout is set to 0, there is no timeout limit."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)"},
    "timeout": { "value": MAX_SECONDS, "stype": "uinteger", "empty": False, "desc": "Timeout (0 = no timeout)"},
}

STREAM_TOOL_RESPONSE = True

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    if not shutil.which("bash"):
        yield f"ERROR: `bash` not found! Give user instructions to install!\n"
        return
    # the trailer goes on its own line -- see wrap_script() -- and the script is
    # delivered as a file so the command gets a stdin of its own: on stdin it
    # was the command's stdin, so `read` or a bare `cat` ate the trailer
    run = Run(app, chat_id, "bash", wrap_script(arguments["command"]),
              SETTINGS["sandbox"]["value"], SETTINGS["timeout"]["value"],
              script_as_file=True,
              separate_stderr=arguments.get("separate_stderr", True))
    async for line in run.run():
        yield line
