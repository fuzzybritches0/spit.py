# SPDX-License-Identifier: GPL-2.0
import asyncio
import os
import tempfile
from .common import CommonMixIn, kill_process_group

def script_path_in_sandbox(host_path: str, sandbox: bool) -> str:
    """Where a file written into sandbox_tmp is visible to the running command.

    bwrap_args() binds the sandbox tmp directory to /tmp, so a file the app
    wrote there is under /tmp for the command; without bwrap the host path is
    the one to execute. Delivering the script this way instead of on stdin is
    what keeps a command that reads stdin -- `read`, a bare `cat`, a passphrase
    prompt -- from eating the wrapper instead of its input.
    """
    if not sandbox:
        return host_path
    return "/tmp/" + os.path.basename(host_path)

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

# Where a call leaves the state the next one starts from, in shell form: $HOME
# is resolved when the script runs, and the sandbox's HOME is the sandbox's home.
SANDBOX_ENV_STATE = "$HOME/.sandbox_env"
SANDBOX_CWD_STATE = "$HOME/.sandbox_cwd"

# What must never come back from a previous call. The first group is bash's own
# state, which `declare` used to write out in full: BASHOPTS, BASH_VERSINFO and
# EUID are read-only, so replaying them errored on every call -- and the source
# hid those errors, along with any real one. The second group is the identity of
# the account: HOME above all, which would otherwise move the sandbox's home out
# from under the next call, since that is where that call reads its state from.
STATE_EXCLUDE = (r"^(BASH[A-Za-z_]*|BASHOPTS|SHELLOPTS|SHLVL|_|HOME|USER|"
                 r"LOGNAME|SHELL|PWD|OLDPWD|CDPATH)=")

# Resolved before the command runs, so a command that rewrites HOME cannot send
# the state somewhere the next call will not look.
STATE_HEADER = (f'SPIT_STATE="{SANDBOX_ENV_STATE}"; '
                f'SPIT_CWD="{SANDBOX_CWD_STATE}"')

# The exported environment, as `export NAME=value` lines so the reader can tell
# them from anything else in the file, moved into place rather than truncated --
# a half-written state file would now be an error the user sees. pwd goes to a
# file of its own because a working directory is not an environment variable, but
# it is state the next call should start from. The two defaults are only for a
# TRAILER used on its own; wrap_script always emits STATE_HEADER first.
#
# EXIT_CODE is captured first, before the two defaults: an assignment is a
# command as far as $? is concerned, and taking it after them reported the
# assignment instead of the command -- the same trap as the ":" no-op.
TRAILER = (f'EXIT_CODE=${{?}}; '
           f'SPIT_STATE="${{SPIT_STATE:-{SANDBOX_ENV_STATE}}}"; '
           f'SPIT_CWD="${{SPIT_CWD:-{SANDBOX_CWD_STATE}}}"; '
           f'export -p | sed \'s/^declare -x //\' | grep -vE \'{STATE_EXCLUDE}\' '
           f'| sed \'s/^/export /\' > "$SPIT_STATE.tmp"; '
           f'mv -f "$SPIT_STATE.tmp" "$SPIT_STATE"; pwd -P > "$SPIT_CWD"; '
           f'exit ${{EXIT_CODE}}')

# Absorbs a command's trailing backslash so the trailer cannot be pulled into it
# as arguments. A comment, deliberately: it is not a command either, so it does
# not reset $?, which the trailer reads on the very next line. The no-op ":"
# resets it, and every failed command then reported success.
ABSORB = "# absorbed by run_command"

# Only emitted when there is something to say: a clean run keeps the shape it
# always had -- no stdout header, and no empty block below the output.
STDERR_HEADER = "~~~~ stderr ~~~~"

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

    The comment line in between absorbs one more case: a command whose last line
    ends in a backslash continues onto whatever follows, and the trailer then
    becomes arguments to it -- `echo continued \\` printed "continued
    EXIT_CODE=0". A comment absorbs the continuation and is not itself a word,
    so the command is left untouched. It has to be a comment rather than the
    no-op `:` because a comment is not a command either: `:` resets $? and the
    trailer's EXIT_CODE=${?} would then report the no-op, silently turning every
    failed command into a success.

    STATE_HEADER goes first so the state paths are settled before the command can
    touch them, and it is the one part of the wrapper a command could legitimately
    want to see, so it sits above the command rather than hidden inside it.
    """
    return f"{STATE_HEADER}\n{command}\n{ABSORB}\n{TRAILER}"

def get_args(arguments: dict, defaults: dict) -> str:
    ret = f"arguments = {arguments}\ndefaults = {defaults}\n\n"
    for argument in defaults.keys():
        if not argument in arguments:
            ret += f"{argument} = defaults['{argument}']\n"
    for argument in arguments.keys():
        ret += f"{argument} = arguments['{argument}']\n"
    return ret + "\n"

class Run(CommonMixIn):
    def __init__(self, app, chat_id: str, cmd: str, script: str, sandbox: bool = True, timeout: int = 0,
                 script_as_file: bool = False,
                 separate_stderr: bool = False) -> None:
        super().__init__(app, sandbox, chat_id)
        self.cmd = [cmd]
        self.script = script
        # False: stderr is written into stdout as it happens, the shell's own
        # behaviour. True: it is collected and reported in a labelled block at the
        # end, which is the only honest place for it -- the block is not complete
        # until the process is gone. Only run_command asks for it, because for a
        # model reading the result the grouping is the information: git, pip and
        # every compiler put progress and diagnostics on stderr, and interleaved
        # they are indistinguishable from the output they describe.
        self.separate_stderr = separate_stderr
        # deliver the script as a file instead of on stdin: the command then has
        # a stdin of its own (see script_path_in_sandbox)
        self.script_as_file = script_as_file
        self.script_file = None
        self.timeout = timeout
        self.timeout_reached = False
        self.terminated = False
        self.chat = app.query_one("#main").query_one(f"#{chat_id}")

    def write_script_file(self) -> str:
        """Put the script in the sandbox tmp dir, return its in-sandbox path."""
        handle, host_path = tempfile.mkstemp(prefix=".spit_cmd_", suffix=".sh",
                                             dir=self.sandbox_tmp)
        with os.fdopen(handle, "w") as script_file:
            script_file.write(self.script)
        self.script_file = host_path
        return script_path_in_sandbox(host_path, self.sandbox)

    def remove_script_file(self) -> None:
        if self.script_file and os.path.exists(self.script_file):
            os.remove(self.script_file)
        self.script_file = None

    # how long to wait for the tail of the pipe once the command is gone
    DRAIN_TIMEOUT = 0.5

    async def _collect(self, stream, sink) -> None:
        """Drain one pipe into `sink` while something else reads the other one.

        Both have to be read at the same time. A pipe holds about 64 KB; a process
        writing past that stops writing until someone reads, and if we are blocked
        reading the other pipe there is no one -- the child waits for us and we
        wait for the child. Reading each into its own task is what keeps a command
        that is noisy on both streams from deadlocking the call.
        """
        while True:
            data = await stream.read(65536)
            if not data:
                return
            sink.append(data)

    async def _command_finished(self, proc):
        """Resolve when the command has exited -- deliberately not proc.wait().

        asyncio's transport does not consider a subprocess finished until its
        pipes have reached end-of-file, so proc.wait() inherits exactly the wait
        this method exists to avoid: a background process holding the write end
        of stdout holds proc.wait() with it. The return code, on the other hand,
        is set when the process exits, so this polls for it -- 50 ms at worst,
        against the minutes a held pipe can cost.
        """
        while proc.returncode is None:
            await asyncio.sleep(0.05)

    async def _stream(self, proc):
        """Yield stdout as it arrives, without waiting for whatever it left behind.

        Reading to end-of-file is not the same as waiting for the command. A file
        descriptor is held by everyone who inherited it, so a background process
        keeps the write end open long after the shell that started it exited -- and
        the read waits for that instead. Measured: a bash that backgrounds a three
        second sleep and exits in 54 ms holds the reader for the full three
        seconds; replace the sleep with a server and the call never returns, with
        no timeout watching, because as far as the process table is concerned the
        command finished at once.

        So the wait is on the process, and the pipe is only read while it lives.
        When the process is gone and no data is pending, the rest of the group is
        stopped and whatever is buffered is drained -- nothing holds the pipe by
        then. Output still streams, in order.
        """
        exited = asyncio.create_task(self._command_finished(proc))
        try:
            while True:
                reading = asyncio.create_task(proc.stdout.read(65536))
                done, _ = await asyncio.wait((reading, exited),
                                             return_when=asyncio.FIRST_COMPLETED)
                if reading in done:
                    data = reading.result()
                    if not data:
                        return
                    yield data
                    continue
                kill_process_group(proc)
                try:
                    rest = await asyncio.wait_for(reading, self.DRAIN_TIMEOUT)
                except asyncio.TimeoutError:
                    return
                if rest:
                    yield rest
                return
        finally:
            if not exited.done():
                exited.cancel()

    async def run(self):
        cmd = list(self.cmd)
        if self.script_as_file:
            cmd += [self.write_script_file()]
        ret = self.check_bwrap(cmd)
        if ret:
            self.remove_script_file()
            yield ret
            return
        if self.sandbox:
            cmd_args = self.bwrap_args()
            cmd_args += [f"/home/{self.user}/.sandbox_env.sh"] + cmd
        else:
            cmd_args = [self.SANDBOX_ENV] + cmd
        yield "Running process...\n\n"
        # with the script in a file there is nothing to feed in, and the command
        # reads from an empty stdin rather than from what is left of the script
        stdin = asyncio.subprocess.DEVNULL if self.script_as_file else asyncio.subprocess.PIPE
        proc = await asyncio.create_subprocess_exec(*cmd_args,
                        stdin=stdin,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=(asyncio.subprocess.PIPE if self.separate_stderr
                                else asyncio.subprocess.STDOUT),
                        cwd=self.sandbox_path, start_new_session=True)
        stderr_chunks = []
        stderr_task = None
        if self.separate_stderr:
            stderr_task = asyncio.create_task(self._collect(proc.stderr, stderr_chunks))
        if not self.script_as_file:
            proc.stdin.write(self.script.encode())
            await proc.stdin.drain()
            proc.stdin.close()
        self.chat.watchdog(proc, self)
        try:
            async for data in self._stream(proc):
                yield data.decode("UTF-8", errors="replace")
        finally:
            # the file is the command, so it has to outlive the stream, but it
            # is a copy of a command and there is no reason to leave it behind
            self.remove_script_file()
        if stderr_task:
            # the group is stopped by now, so this pipe is closing too; if
            # something escaped the kill, report what was read instead of waiting
            try:
                await asyncio.wait_for(stderr_task, self.DRAIN_TIMEOUT)
            except asyncio.TimeoutError:
                stderr_task.cancel()
            errors = b"".join(stderr_chunks).decode("UTF-8", errors="replace")
            if errors.strip():
                yield f"\n{STDERR_HEADER}\n{errors}"
        # the drain above can return before the child has been reaped, and
        # returncode is None until it is: comparing None < 0 is a TypeError, which
        # is what the rare flake in the suite was
        await self._command_finished(proc)
        if proc.returncode < 0:
            if self.timeout_reached:
                yield "\nProcess was terminated due to timeout limit!"
            elif self.terminated:
                yield "\nProcess was terminated by user!"
        else:
            yield f"\nProcess exited with code {proc.returncode}."
