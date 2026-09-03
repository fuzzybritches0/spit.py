# SPDX-License-Identifier: GPL-2.0
import asyncio
from .common import CommonMixIn

def get_script(tool, common: str = "") -> str:
    ret = ""
    script_dir = "/".join(tool.split("/")[0:-1])
    script = tool.split("/")[-1]
    script_path = script_dir + "/scripts/" + script
    if common:
        common_path = script_dir + "/scripts/common/" + common + ".py"
        with open(common_path, "r") as f:
            common = f.read() + "\n"
    with open(script_path, "r") as f:
        return common + f.read()

SANDBOX_ENV_STATE = "~/.sandbox_env"

TRAILER = (f"EXIT_CODE=${{?}}; declare > {SANDBOX_ENV_STATE}; "
           f"export -p >> {SANDBOX_ENV_STATE}; exit ${{EXIT_CODE}}")

def wrap_script(command: str) -> str:
    """A command plus the trailer that carries exit code and shell state out.

    The trailer goes on a line of its own and must not be prefixed with ";".
    Both halves of that matter:

      * glued to the last line ("cmd; TRAILER"), a command whose last line is a
        here-document delimiter never ends its here-document: bash reads to end
        of input, warns, and hands the trailer to the here-document -- into the
        very file the command was writing. A command ending in a comment
        swallows the trailer the same way, and the environment silently stops
        being saved.
      * on its own line but still starting with ";", bash refuses the whole
        script: "syntax error near unexpected token `;'".

    Bare, on its own line, is the only form that survives both.
    """
    return f"{command}\n{TRAILER}"

def get_args(arguments: dict, defaults: dict) -> str:
    ret = f"arguments = {arguments}\ndefaults = {defaults}\n\n"
    for argument in defaults.keys():
        if not argument in arguments:
            ret += f"{argument} = defaults['{argument}']\n"
    for argument in arguments.keys():
        ret += f"{argument} = arguments['{argument}']\n"
    return ret + "\n"

class Run(CommonMixIn):
    def __init__(self, app, chat_id: str, cmd: str, script: str, sandbox: bool = True, timeout: int = 0) -> None:
        super().__init__(app, sandbox, chat_id)
        self.cmd = [cmd]
        self.script = script
        self.timeout = timeout
        self.timeout_reached = False
        self.terminated = False
        self.chat = app.query_one("#main").query_one(f"#{chat_id}")

    async def run(self):
        ret = self.check_bwrap(self.cmd)
        if ret:
            yield ret
            return
        if self.sandbox:
            cmd_args = self.bwrap_args()
            cmd_args += [f"/home/{self.user}/.sandbox_env.sh"] + self.cmd
        else:
            cmd_args = [self.SANDBOX_ENV] + self.cmd
        yield "Running process...\n\n"
        proc = await asyncio.create_subprocess_exec(*cmd_args,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        cwd=self.sandbox_path, start_new_session=True)
        proc.stdin.write(self.script.encode())
        await proc.stdin.drain()
        proc.stdin.close()
        self.chat.watchdog(proc, self)
        async for data in proc.stdout:
            yield data.decode("UTF-8", errors="replace")
        if proc.returncode < 0:
            if self.timeout_reached:
                yield "\nProcess was terminated due to timeout limit!"
            elif self.terminated:
                yield "\nProcess was terminated by user!"
        else:
            yield f"\nProcess exited with code {proc.returncode}."
