#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for run.wrap_script(), the trailer run_command() appends.

The trailer carries the exit code and the shell environment back out of the
sandbox. It used to be glued onto the end of the command with a ";", which
holds only while the command is a single simple line:

  * a command whose last line is a here-document delimiter never terminates the
    here-document. bash reads to end of input, warns "here-document delimited
    by end-of-file", and hands the trailer to the here-document -- into the
    file the command was writing.
  * a command ending in a comment swallows the trailer too, so `declare >
    ~/.sandbox_env` never runs and exported variables silently stop persisting
    between calls -- visible only as the next call forgetting something.

Putting the trailer on its own line fixes both, but only if the leading ";"
goes with the newline: a statement list may not begin with ";", and bash then
rejects the entire script.

bash is fed the script on stdin here exactly as Run.run() does it, and HOME is
pointed at a temporary directory so ~/.sandbox_env lands there.
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.tools.run.run import ABSORB, TRAILER, wrap_script  # noqa: E402

OLD = ";" + TRAILER          # how run_command.py assembled it before

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def bash(script: str, home: str):
    """Run a script the way Run.run() does: bash, script on stdin."""
    env = dict(os.environ)
    env["HOME"] = home
    return subprocess.run(["bash"], input=script, capture_output=True, text=True,
                          cwd=home, env=env)


def state(home: str) -> str:
    path = os.path.join(home, ".sandbox_env")
    return open(path).read() if os.path.exists(path) else ""


def has_var(dump: str, name: str) -> bool:
    """Was `name` assigned in the shell that wrote the dump?

    Substring tests are not enough: when the trailer is swallowed, bash files
    the eaten assignment in its "_" variable, so the state reads "_=EXIT_CODE=0"
    and still contains the name.
    """
    return any(line.startswith(name + "=") for line in dump.splitlines())


HEREDOC = "cat > out.txt <<'EOF'\nfirst line\nsecond line\nEOF"

print("=== 1. Shape of the wrapped script ===")
wrapped = wrap_script("true")
lines = wrapped.splitlines()
check("t1-command-first", lines[0], "true")
check("t1-trailer-last", lines[-1], TRAILER)
check("t1-trailer_line", lines[-1].startswith("EXIT_CODE="), True)
check("t1-no-glued-semicolon", "; EXIT_CODE" in wrapped, False)
heredoc_lines = wrap_script(HEREDOC).splitlines()
check("t1-delimiter-alone", "EOF" in heredoc_lines, True)
check("t1-delimiter-before-trailer",
      heredoc_lines.index("EOF") < len(heredoc_lines) - 1, True)

print()
print("=== 2. Exit codes still reach the caller ===")
with tempfile.TemporaryDirectory() as home:
    for command, expected in (("true", 0), ("exit 3", 3),
                              ("ls /definitely-not-here", 2),
                              ("echo a\necho b", 0)):
        check(f"t2-rc-{command.splitlines()[0]}",
              bash(wrap_script(command), home).returncode, expected)

print()
print("=== 3. A here-document is no longer polluted ===")
with tempfile.TemporaryDirectory() as home:
    proc = bash(wrap_script(HEREDOC), home)
    check("t3-rc", proc.returncode, 0)
    check("t3-no-warning", "warning" in proc.stderr.lower(), False)
    written = open(os.path.join(home, "out.txt")).read()
    check("t3-content", written, "first line\nsecond line\n")
    check("t3-no-trailer-in-file", "EXIT_CODE" in written, False)
    check("t3-state-exists", os.path.exists(os.path.join(home, ".sandbox_env")), True)

print()
print("=== 4. A command ending in a comment still saves the environment ===")
with tempfile.TemporaryDirectory() as home:
    proc = bash(wrap_script("export SPIT_KEPT=yes # trailing comment"), home)
    check("t4-rc", proc.returncode, 0)
    check("t4-variable-persisted", "SPIT_KEPT" in state(home), True)
    check("t4-no-stray-output", "EXIT_CODE" in proc.stdout, False)

print()
print("=== 5. Control: the old glue fails 3 and 4 ===")
with tempfile.TemporaryDirectory() as home:
    proc = bash(HEREDOC + OLD, home)
    written = open(os.path.join(home, "out.txt")).read()
    check("t5-file-polluted", "EXIT_CODE" in written, True)
    check("t5-warning-shown", "warning" in proc.stderr.lower(), True)
with tempfile.TemporaryDirectory() as home:
    bash("export SPIT_KEPT=yes # trailing comment" + OLD, home)
    check("t5-environment-lost", "SPIT_KEPT" in state(home), False)

print()
print("=== 6. A command ending in a backslash ===")
CONTINUED = "echo continued \\"
lines = wrap_script(CONTINUED).splitlines()
check("t6-absorb-line-present", ABSORB in lines, True)
check("t6-absorb-last-before-trailer", lines[-2], ABSORB)
check("t6-absorb-is-a-comment", ABSORB.startswith("#"), True)
with tempfile.TemporaryDirectory() as home:
    proc = bash(wrap_script(CONTINUED), home)
    check("t6-rc", proc.returncode, 0)
    check("t6-output", proc.stdout.strip(), "continued")
    check("t6-no-trailer-in-output", "EXIT_CODE" in proc.stdout, False)
    check("t6-state-saved", has_var(state(home), "EXIT_CODE"), True)

print()
print("=== 7. Control: without the absorb line the trailer is swallowed ===")
with tempfile.TemporaryDirectory() as home:
    proc = bash(CONTINUED + "\n" + TRAILER, home)
    check("t7-trailer-became-arguments", "EXIT_CODE" in proc.stdout, True)
    # the assignment was eaten as an argument and ended up in bash's "_" instead
    # of being executed, so the trailer ran with no exit code of its own
    check("t7-exit-code-never-assigned", has_var(state(home), "EXIT_CODE"), False)
    check("t7-landed-in-last-argument", "_=EXIT_CODE=" in state(home), True)

print()
print("=== 8. A failing command keeps its code through the absorb line ===")
for command, expected in (("ls /definitely-not-here", 2), ("exit 7", 7),
                          ("false", 1)):
    with tempfile.TemporaryDirectory() as home:
        check(f"t8-rc-{command}", bash(wrap_script(command), home).returncode,
              expected)

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
