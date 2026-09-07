# SPDX-License-Identifier: GPL-2.0
import shutil
from pathlib import Path
from spit_app.tools.run.run import Run, wrap_script
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Run a script with any interpreter allowed.",
        "parameters": {
            "type": "object",
            "properties": {
                "interpreter": {
                    "type": "string",
                    "description": ("The interpreter to run the script with. It must be one "
                                    "of the allowed interpreters named in the instructions; "
                                    "anything else is refused before anything runs")
                },
                "script": {
                    "type": "string",
                    "description": "Script or a path to a script file."
                },
                "separate_stderr": {
                    "type": "boolean",
                    "description": ("Report stderr in a labelled section after the output "
                                    "rather than interleaved with it. Default: true; set "
                                    "false when the two streams form one dialogue whose "
                                    "order matters")
                }
            },
            "required": ["interpreter", "script"]
        }
    }
}

OUTPUT_TYPE_HINT = "text"

SANDBOX = True
MAX_SECONDS = 0
ALLOWED = "bash, python3, perl"
PROMPT = "Use this function to run a script with any interpreter on the allowed list and receive its output; a name outside that list is refused before anything runs, and only the user can widen it in the `interpreters` setting. `script` is the script itself or the path of a file to run. stderr is reported in a `~~~~ stderr ~~~~` block after the output, and only when there is stderr; set `separate_stderr=false` to interleave the two streams when their relative order is the point. Every call starts from the shell state the previous one left behind, but only a shell script writes any back: the state is saved by bash, so variables a python or perl script sets die with it."
PROMPT_INST = "The following interpreters are allowed: [interpreters]. Timeout is set to [timeout]. When timeout is set to 0, there is no timeout limit."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "sandbox": { "value": SANDBOX, "stype": "boolean", "desc": "Run in sandbox (DANGER: Do not deactivate!)"},
    "timeout": { "value": MAX_SECONDS, "stype": "uinteger", "empty": False, "desc": "Timeout (0 = no timeout)"},
    "interpreters": {"value": ALLOWED, "stype": "text", "empty": False, "desc": "Allowed interpreters (enforced: every other name is refused)"}
}

STREAM_TOOL_RESPONSE = True

# Only bash gets the wrapper, and the reason is what it costs the others.
# wrap_script() is bash code, so prepended to a python or perl script it is a
# SyntaxError on the first trailer line -- and both parse the whole file before
# executing any of it, so the script's own output never appears at all and the
# model gets a traceback quoting shell it did not write. `sh` parses it (dash,
# measured), but the trailer saves the state through `export -p | sed
# 's/^declare -x //'`, and the `declare -x` format is bash's own: under dash
# every saved line comes out `export export NAME='value'`. It still sources, so
# the damage is invisible; a state file that is wrong for the tool that reads it
# back is not something to keep on purpose. Everything but bash gets its script
# verbatim and simply has no shell state to carry -- which is what it had
# before the wrapper arrived here, and what it still gets from sandbox_env.sh
# when a previous bash call left some.
SHELL_INTERPRETERS = ("bash",)

def allowed_interpreters(setting: str) -> list:
    """The interpreter names the user allows, read out of the free-text setting.

    The default separates with ", " but a user types this field by hand, so
    commas and whitespace separate alike: one name per line, no commas at all,
    and an `a,,b` all yield the list that was meant (`split()` drops the empty
    pieces). Names are compared as written, because they are program names and
    the file system does distinguish `Python3` from `python3` -- the refusal
    lists what is allowed, so a typo there is diagnosable rather than
    mysterious. The str() is for a settings file hand-edited into a list or a
    number: the call then refuses with that value quoted back instead of raising
    AttributeError inside the tool, which is the rule the interpreter argument
    follows too.
    """
    return str(setting).replace(",", " ").split()

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    interpreter = arguments["interpreter"]
    # the name that was ASKED for is the name that is checked: the python ->
    # python3 fallback below must never turn a refused name into a run, while a
    # `python` the user did allow may still resolve to python3 the way it always
    # has. Checking first also means a value that is not a name at all (a list
    # left as one by a decoder) is refused here instead of reaching which().
    allowed = allowed_interpreters(SETTINGS["interpreters"]["value"])
    if interpreter not in allowed:
        listed = ", ".join(allowed) if allowed else "nothing (the setting is empty)"
        yield (f"ERROR: `{interpreter}` is not an allowed interpreter! The "
               f"`interpreters` setting allows {listed}. Ask the user to add it "
               f"there if this run really needs it.")
        return
    if interpreter == "python" and not shutil.which("python"):
        interpreter = "python3"
    if not shutil.which(interpreter):
        yield f"ERROR: `{interpreter}` not found! Give user instructions to install!"
        return
    _script = Path(arguments["script"])
    if _script.is_file():
        script = _script.read_text(encoding='utf-8')
        yield f"Reading script from file `{_script}`.\n\n"
    else:
        script = arguments["script"]
    if not script.strip():
        yield "ERROR: script is empty!"
        return
    run = Run(app, chat_id, interpreter,
              wrap_script(script) if interpreter in SHELL_INTERPRETERS else script,
              SETTINGS["sandbox"]["value"], SETTINGS["timeout"]["value"],
              script_as_file=True,
              separate_stderr=arguments.get("separate_stderr", True))
    async for line in run.run():
        yield line
