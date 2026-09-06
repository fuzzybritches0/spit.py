#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for the payloads `run_script` builds, run through real interpreters.

`test_interpreters.py` pins the call the tool makes. This one takes those exact
payloads -- built by calling the tool, never rebuilt here -- and runs them with
bash, python3 and perl, because the defect being pinned is a *parse* failure:
the wrong payload does not fail in the wiring, it fails inside the interpreter,
and only a real interpreter can see it. The wrapper arrives on a line the script
never had, and python and perl parse the whole file before executing any of it,
so nothing of the script's own output is produced: the tool returns a traceback
quoting shell.

Delivery follows `Run`: the payload goes in a file named `.sh` (that is what
`Run.write_script_file` calls it) on an empty stdin. The `.sh` suffix on a python
script is part of what is pinned -- it must not matter.

The controls (the wrapped form of the python and perl scripts, i.e. what this
tool delivered before the fix) are what make the positive checks mean something.
perl is one of the three interpreters the tool's default allowed setting names
but is not guaranteed on every test machine, so its two checks report a verdict
(`absent` / `refused` / `ran`) against what the environment actually offers --
the count does not move with the machine, and a perl that is installed and
broken still fails.
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.tools.run.run import wrap_script   # noqa: E402
from stub_run import build                       # noqa: E402

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def execute(interpreter, payload, home):
    """Run a payload the way Run does: as a file, on an empty stdin, in `home`."""
    with tempfile.TemporaryDirectory() as root:
        path = os.path.join(root, "delivered.sh")
        with open(path, "w") as handle:
            handle.write(payload)
        return subprocess.run([interpreter, path], capture_output=True,
                              text=True, cwd=root, stdin=subprocess.DEVNULL,
                              env={**os.environ, "HOME": home})


def state_file(home):
    path = os.path.join(home, ".sandbox_env")
    return open(path).read() if os.path.exists(path) else ""


def perl_verdict(ran_ok, refused):
    """`absent`, or what a real perl did with the payload it was given."""
    if not shutil.which("perl"):
        return "absent"
    if ran_ok:
        return "ran"
    return "refused" if refused else "broke"


print("=== 1. python3 runs what the tool built for it ===")
with tempfile.TemporaryDirectory() as home:
    built, text = build("python3", "print('rs-one-python')")
    proc = execute("python3", built.script, home)
    check("t1-exit-code", proc.returncode, 0)
    check("t1-own-output-appears", "rs-one-python" in proc.stdout, True)
    check("t1-no-syntax-error", "SyntaxError" in proc.stderr, False)
    check("t1-no-shell-in-sight", "EXIT_CODE" in proc.stderr + proc.stdout, False)
    check("t1-no-state-written", state_file(home), "")

print()
print("=== 2. Control: the same script wrapped does not run at all ===")
with tempfile.TemporaryDirectory() as home:
    proc = execute("python3", wrap_script("print('rs-two-python')"), home)
    check("t2-exits-badly", proc.returncode != 0, True)
    check("t2-syntax-error", "SyntaxError" in proc.stderr, True)
    check("t2-script-never-ran", "rs-two-python" in proc.stdout, False)
    check("t2-trailer-named-in-the-traceback", "EXIT_CODE" in proc.stderr, True)

print()
print("=== 3. A script that is not a shell still gets stderr where it belongs ===")
with tempfile.TemporaryDirectory() as home:
    built, text = build("sh", "echo rs-three-sh")
    proc = execute("sh", built.script, home)
    check("t3-sh-exit-code", proc.returncode, 0)
    check("t3-sh-own-output", "rs-three-sh" in proc.stdout, True)
    check("t3-sh-no-wrapper", "EXIT_CODE" in proc.stdout + proc.stderr, False)
    check("t3-sh-no-state-written", state_file(home), "")

print()
print("=== 4. bash gets the wrapper, and it does what it is for ===")
with tempfile.TemporaryDirectory() as home:
    built, text = build("bash", "export SPIT_RS_FOUR=yes; echo rs-four-bash")
    check("t4-payload-wrapped", built.script,
          wrap_script("export SPIT_RS_FOUR=yes; echo rs-four-bash"))
    proc = execute("bash", built.script, home)
    check("t4-exit-code", proc.returncode, 0)
    check("t4-own-output", "rs-four-bash" in proc.stdout, True)
    check("t4-no-trailer-in-output", "EXIT_CODE" in proc.stdout, False)
    check("t4-state-saved", "SPIT_RS_FOUR" in state_file(home), True)
with tempfile.TemporaryDirectory() as home:
    built, text = build("bash", "echo rs-four-rc; exit 7")
    proc = execute("bash", built.script, home)
    check("t4-script-exit-code-survives-the-trailer", proc.returncode, 7)
with tempfile.TemporaryDirectory() as home:
    built, text = build("bash", "exit 0")
    state = state_file(home)
    check("t4-state-lines-are-bash-shaped",
          all(line.startswith("export ") and not line.startswith("export export ")
              for line in state.splitlines()), True)

print()
print("=== 5. perl: the same rule, measured on a real perl ===")
with tempfile.TemporaryDirectory() as home:
    built, text = build("perl", "print 'rs-five-perl\\n';")
    proc = execute("perl", built.script, home) if shutil.which("perl") else None
    check("t5-perl-runs-its-own-script",
          perl_verdict(proc is not None and proc.returncode == 0
                       and "rs-five-perl" in proc.stdout
                       and "EXIT_CODE" not in proc.stderr, False),
          "absent" if not shutil.which("perl") else "ran")
with tempfile.TemporaryDirectory() as home:
    wrapped = wrap_script("print 'rs-five-wrapped\\n';")
    proc = execute("perl", wrapped, home) if shutil.which("perl") else None
    check("t5-perl-refuses-the-wrapper",
          perl_verdict(False, proc is not None and proc.returncode != 0
                       and "syntax error" in proc.stderr.lower()
                       and "rs-five-wrapped" not in proc.stdout),
          "absent" if not shutil.which("perl") else "refused")

print()
print("=== 6. The file-path form runs as well as the inline one ===")
with tempfile.TemporaryDirectory() as root:
    path = os.path.join(root, "t6-script.py")
    with open(path, "w") as handle:
        handle.write("print('rs-six-from-file')\n")
    built, text = build("python3", path)
    check("t6-read-from-the-file", "rs-six-from-file" in built.script, True)
    with tempfile.TemporaryDirectory() as home:
        proc = execute("python3", built.script, home)
        check("t6-exit-code", proc.returncode, 0)
        check("t6-output", "rs-six-from-file" in proc.stdout, True)
    with tempfile.TemporaryDirectory() as home:
        proc = execute("python3", wrap_script(open(path).read()), home)
        check("t6-control-wrapped-does-not-run", proc.returncode != 0, True)

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
