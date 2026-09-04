#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for how a script reaches the shell, and what stdin the command gets.

Run.run() used to write every script to the child's stdin. bash reads a script
from stdin *as it executes it*, so a command that reads stdin consumed the
wrapper rather than its own input:

    $ export SPIT_STDIN=yes; read FOO; echo "read: [$FOO]"
    read: [EXIT_CODE=${?}; declare > ~/.sandbox_env; ...]

The trailer was gone: the environment was not saved and the exit code reported
was whatever had run last. Delivering the script as a file, with the child on an
empty stdin, gives the command a stdin of its own.

The Run instance is driven through the shared harness in stub_app.py for the
reasons given there.
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.tools.run.run import script_path_in_sandbox, wrap_script  # noqa: E402
from stub_app import run_as_file                                        # noqa: E402

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def state(home: str) -> str:
    path = os.path.join(home, ".sandbox_env")
    return open(path).read() if os.path.exists(path) else ""


def has_var(dump: str, name: str) -> bool:
    """Was `name` exported into the state? It is written as `export NAME=value`."""
    return any(line.startswith(prefix + name + "=")
               for line in dump.splitlines() for prefix in ("export ", ""))


READING = "export SPIT_DELIV=yes; read FOO; echo \"read: [$FOO]\""

print("=== 1. Where the delivered file lives ===")
check("t1-sandboxed", script_path_in_sandbox("/host/dir/.spit_cmd_1.sh", True),
      "/tmp/.spit_cmd_1.sh")
check("t1-unsandboxed", script_path_in_sandbox("/host/dir/.spit_cmd_1.sh", False),
      "/host/dir/.spit_cmd_1.sh")

print()
print("=== 2. A command that reads stdin no longer eats the wrapper ===")
with tempfile.TemporaryDirectory() as root:
    home = os.path.join(root, "h")
    os.makedirs(home, exist_ok=True)
    out, _, _ = run_as_file(wrap_script(READING), home, root)
    check("t2-read-got-eof", 'read: []' in out, True)
    check("t2-no-trailer-in-output", "EXIT_CODE" in out, False)
    check("t2-environment-saved", has_var(state(home), "SPIT_DELIV"), True)
    check("t2-report-line", "Process exited with code 0" in out, True)

print()
print("=== 3. A bare cat gets an empty stdin ===")
with tempfile.TemporaryDirectory() as root:
    home = os.path.join(root, "h")
    os.makedirs(home, exist_ok=True)
    out, _, _ = run_as_file(wrap_script("export SPIT_CAT=yes; cat"), home, root)
    check("t3-nothing-read", "EXIT_CODE" in out, False)
    check("t3-environment-saved", has_var(state(home), "SPIT_CAT"), True)

print()
print("=== 4. The delivered file is cleaned up, and exit codes survive ===")
with tempfile.TemporaryDirectory() as root:
    home = os.path.join(root, "h")
    os.makedirs(home, exist_ok=True)
    out, leftovers, _ = run_as_file(wrap_script("exit 5"), home, root)
    check("t4-exit-code", "Process exited with code 5" in out, True)
    check("t4-no-leftovers", leftovers, [])

print()
print("=== 5. Control: the same commands with the script on stdin ===")
with tempfile.TemporaryDirectory() as home:
    # reading to EOF takes the wrapper with it: nothing was saved
    proc = subprocess.run(["bash"], input=wrap_script("export SPIT_CTL=yes; cat"),
                          capture_output=True, text=True, cwd=home,
                          env={**os.environ, "HOME": home})
    check("t5-wrapper-eaten", "EXIT_CODE" in proc.stdout, True)
    check("t5-environment-lost", has_var(state(home), "SPIT_CTL"), False)
with tempfile.TemporaryDirectory() as home:
    # a single read is saved only by the absorb line, and lands the wrapper in
    # the user's own variable -- proof that stdin delivery is not workable
    proc = subprocess.run(["bash"], input=wrap_script(READING),
                          capture_output=True, text=True, cwd=home,
                          env={**os.environ, "HOME": home})
    check("t5b-into-the-users-variable", "absorbed by run_command" in proc.stdout,
          True)

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
