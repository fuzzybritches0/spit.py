#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for the interpreter the built-in tool scripts run under.

A tool's script reaches python3 on stdin, and stdin mode puts '' -- the current
working directory -- first on sys.path. The working directory is state:
run_command's `cd` carries over to the next call, so a call that ended inside a
python package directory left the NEXT file tool importing that directory in
place of the standard library. Measured on this box with the state pointing at
site-packages/textual, whose types.py shadows the stdlib one:

    write_file -> File "/usr/lib/python3.14/pathlib/__init__.py" ...
                  File ".../site-packages/textual/types.py", line 5
                  ModuleNotFoundError: No module named 'textual'

and the file was not written. Which tool died was decided by its own import
graph and never by the target file: in the same poisoned directory read_files.py
(importing nothing) answered normally and search_replace.py (re -> enum -> types)
did not. The same shape arrives through the OTHER half of the state: an exported
PYTHONPATH naming a directory with a types.py in it poisons a later tool call
with the working directory perfectly clean (section 5).

TOOL_PYTHON (`python3 -E -s -P`) closes both doors: -P keeps the interpreter's
start-up directory off sys.path, -E keeps the inherited environment off it, -s
keeps the user's site-packages out of a stdlib-only script. It deliberately does
not touch the working directory, so a relative `path` argument means what it
meant before (section 4). That is why this is the fix and why "do not load the
state for the file tools" is not: that moves the tool instead of closing the
door, and it sends a relative write_file into the sandbox home in silence.

Each "call" is the real chain Run builds for these tools -- sandbox_env.sh, then
the interpreter with the program on stdin -- against a HOME holding the state a
previous call left behind, as in test_state.py. No bwrap: what is under test is
the interpreter's path, and the sandbox changes nothing about it.
"""
import importlib
import os
import subprocess
import sys
import sysconfig
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spit_app.tools.run.run import TOOL_PYTHON, Run, get_args, get_script  # noqa: E402
from stub_app import StubApp                                              # noqa: E402

SANDBOX_ENV_SH = os.path.join(REPO_ROOT, "spit_app", "tools", "run", "sandbox_env.sh")
STDLIB = sysconfig.get_paths()["stdlib"]

# A stdlib name every file tool's import graph reaches (pathlib -> glob ->
# contextlib -> functools -> types) and a token that cannot appear by accident
# (TRAPS #8).
POISON = "types.py"
TOKEN = "mm-shadow-poison"

TOOL_MODULES = ["delete_lines", "diff", "file_info", "find_files", "grep",
                "insert_lines", "list_directory", "patch", "read_files", "remove",
                "rename", "search_replace", "write_file"]

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def call(home: str, program: str, interpreter: list):
    """One tool call, as Run delivers it: sandbox_env.sh -> interpreter <- stdin."""
    script = os.path.join(home, ".spit_tool.py")
    with open(script, "w") as handle:
        handle.write(program)
    with open(script) as stdin_handle:
        return subprocess.run(["bash", SANDBOX_ENV_SH] + list(interpreter),
                              stdin=stdin_handle, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                                   "HOME": home},
                              cwd=home)


def poisoned_cwd(home: str) -> str:
    """A directory holding a stdlib name that raises: the next call's cwd."""
    target = os.path.join(home, "pkgdir")
    os.mkdir(target)
    with open(os.path.join(target, POISON), "w") as handle:
        handle.write(f"raise RuntimeError('{TOKEN} was imported')\n")
    return target


def state(home: str, cwd: str = None, env_lines: list = None) -> None:
    if cwd is not None:
        with open(os.path.join(home, ".sandbox_cwd"), "w") as handle:
            handle.write(cwd + "\n")
    if env_lines is not None:
        with open(os.path.join(home, ".sandbox_env"), "w") as handle:
            handle.write("".join(line + "\n" for line in env_lines))


print("=== 1. Control: the bare interpreter does die in the poisoned directory ===")
with tempfile.TemporaryDirectory() as home:
    state(home, cwd=poisoned_cwd(home))
    proc = call(home, "import pathlib\nprint('mm-ran-anyway')\n", ["python3"])
    check("t1-control-dies", proc.returncode != 0, True)
    check("t1-control-imported-the-poison", TOKEN in proc.stdout, True)
    check("t1-control-nothing-ran", "mm-ran-anyway" in proc.stdout, False)

print()
print("=== 2. TOOL_PYTHON runs in that same directory and shadows nothing ===")
with tempfile.TemporaryDirectory() as home:
    target = poisoned_cwd(home)
    state(home, cwd=target)
    proc = call(home,
                "import os, pathlib, re, sys\n"
                "print('cwd', os.getcwd())\n"
                "print('empty-on-path', '' in sys.path)\n"
                "print('pathlib', pathlib.__file__)\n"
                "print('mm-ok')\n", TOOL_PYTHON)
    check("t2-rc", proc.returncode, 0)
    check("t2-ran", "mm-ok" in proc.stdout, True)
    check("t2-no-poison", TOKEN in proc.stdout, False)
    check("t2-cwd-still-the-carried-one", f"cwd {target}" in proc.stdout, True)
    check("t2-cwd-not-on-sys-path", "empty-on-path False" in proc.stdout, True)
    check("t2-pathlib-is-the-stdlib", f"pathlib {STDLIB}" in proc.stdout, True)

print()
print("=== 3. The flags are the three that are claimed ===")
with tempfile.TemporaryDirectory() as home:
    # bool() because the flags print as ints except where CPython already
    # returns a bool (safe_path) -- the check is about them being set.
    proc = call(home, "import sys\nprint(bool(sys.flags.safe_path), "
                      "bool(sys.flags.ignore_environment), "
                      "bool(sys.flags.no_user_site))\n", TOOL_PYTHON)
    check("t3-flags", proc.stdout.strip(), "True True True")
    check("t3-program-is-python3", TOOL_PYTHON[0], "python3")

print()
print("=== 4. A relative path argument still means the carried directory ===")
with tempfile.TemporaryDirectory() as home:
    target = poisoned_cwd(home)
    state(home, cwd=target)
    with open(os.path.join(target, "t.txt"), "w") as handle:
        handle.write("old_word old_word\n")
    with open(os.path.join(home, "t.txt"), "w") as handle:
        handle.write("the one in the sandbox home\n")
    defaults = {"use_regex": False, "max_replacements": 0, "dry_run": False}
    program = get_args({"path": "t.txt", "find": "old_word",
                        "replace": "new_word", **defaults}, defaults)
    program += get_script(os.path.join(REPO_ROOT, "spit_app", "tools",
                                       "search_replace.py"))
    proc = call(home, program, TOOL_PYTHON)
    check("t4-rc", proc.returncode, 0)
    check("t4-replaced", "Replaced 2 of 2 match(es)" in proc.stdout, True)
    with open(os.path.join(target, "t.txt")) as handle:
        check("t4-edited-the-file-in-the-carried-cwd", handle.read(),
              "new_word new_word\n")
    with open(os.path.join(home, "t.txt")) as handle:
        check("t4-did-not-touch-the-home-copy", handle.read(),
              "the one in the sandbox home\n")

print()
print("=== 5. The env half: an exported PYTHONPATH poisons one and not the other ===")
with tempfile.TemporaryDirectory() as home:
    target = poisoned_cwd(home)
    state(home, cwd=home, env_lines=[f"export PYTHONPATH='{target}'"])
    program = "import pathlib\nprint('mm-ran-anyway')\n"
    proc = call(home, program, ["python3"])
    check("t5-control-dies-on-pythonpath", TOKEN in proc.stdout, True)
    proc = call(home, program, TOOL_PYTHON)
    check("t5-no-poison-under-TOOL_PYTHON", TOKEN in proc.stdout, False)
    check("t5-ran", proc.returncode, 0)

print()
print("=== 6. Every script tool declares it ===")
for name in TOOL_MODULES:
    module = importlib.import_module(f"spit_app.tools.{name}")
    check(f"t6-{name}-interpreter", module.EXEC["interpreter"], TOOL_PYTHON)

print()
print("=== 7. Run carries an interpreter with arguments, and a bare name alone ===")
with tempfile.TemporaryDirectory() as root:
    os.makedirs(os.path.join(root, "home"), exist_ok=True)
    os.makedirs(os.path.join(root, "tmp"), exist_ok=True)
    app = StubApp(os.path.join(root, "home"), os.path.join(root, "tmp"))
    check("t7-argv-list-kept", Run(app, "chat1", TOOL_PYTHON, "x").cmd,
          ["python3", "-E", "-s", "-P"])
    check("t7-bare-name-is-a-one-word-argv", Run(app, "chat1", "bash", "x").cmd,
          ["bash"])
    check("t7-first-element-is-the-program",
          Run(app, "chat1", TOOL_PYTHON, "x").cmd[0], "python3")

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
